#!/usr/bin/env python3
"""
二段構えWeb取得（requests → Crawl4AI / Playwright fallback）

Code適応注記:
- 出典: 本家 PhronisisCore scripts/web_fetch.py を移植（2026-11-10）。本体ロジックは不変。
- Codeでは requests+bs4 の stage1 が単独で動く。playwright/crawl4ai は fallback（未導入端末では stage1 のみ）。
- 使用条件・使い分けは knowledge/code_knowledge/web_research.md を参照。

使い方:
  python scripts/web_fetch.py <url>
  python scripts/web_fetch.py --force-crawl4ai <url>
  python scripts/web_fetch.py --no-fallback <url>

第一段: requests + ブラウザUA（軽量・高速）
  → 403/429/空HTML/エンコード不一致 の場合は第二段へ
第二段: Crawl4AI（優先） → 未導入時はPlaywrightに自動フォールバック
  → Crawl4AI: patchright（undetected Chromium）で反クローリング回避 + Markdown出力 + エンコード問題解決
  → Playwright: headless Chromium（JSレンダリング）

Crawl4AI 導入（推奨。価格コム等の文字化け対策＋反ボット回避に有効）:
  pip install crawl4ai
  python -m playwright install chromium

依存: requests, beautifulsoup4, playwright（必須）/ crawl4ai（任意・推奨）
"""
import sys, asyncio, json, os

def write_utf8(text):
    sys.stdout.buffer.write(text.encode("utf-8"))
    sys.stdout.buffer.write(b"\n")
    sys.stdout.buffer.flush()


def stage1_requests(url: str, timeout: int = 15) -> dict:
    import requests as req
    from bs4 import BeautifulSoup

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/147.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ja,en-US;q=0.7,en;q=0.3",
    }
    try:
        resp = req.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        status = resp.status_code
        text = resp.text
        html_lower = text.lower()

        blocked = False
        reason = None
        if status in (403, 429, 503):
            blocked, reason = True, f"HTTP {status}"
        elif status >= 400:
            blocked, reason = True, f"HTTP {status}"
        elif len(text.strip()) < 200:
            blocked, reason = True, f"空/短レスポンス ({len(text.strip())} chars)"
        elif "just a moment" in html_lower or "cf-ray" in html_lower:
            blocked, reason = True, "Cloudflare チャレンジ"
        elif "captcha" in html_lower:
            blocked, reason = True, "CAPTCHA 検出"

        # エンコード不一致検出（例: サーバーがUTF-8詐称してShift-JISを返すケース）
        if not blocked:
            apparent = (resp.apparent_encoding or "").lower().replace("-", "").replace("_", "")
            declared = (resp.encoding or "").lower().replace("-", "").replace("_", "")
            if apparent and declared and apparent != declared:
                jap_encs = {"shiftjis", "eucjp", "iso2022jp", "utf8"}
                if (apparent in jap_encs) != (declared in jap_encs):
                    import re
                    suspicious = len(re.findall(r"[\x80-\x9f]", text[:2000]))
                    if suspicious > 20:
                        blocked, reason = True, f"エンコード不一致（宣言:{resp.encoding} 実体:{resp.apparent_encoding}）"

        soup = BeautifulSoup(text, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        body_text = soup.get_text(separator="\n", strip=True)

        return {
            "success": not blocked,
            "status": status,
            "title": title,
            "text": body_text or text,
            "stage": "requests",
            "blocked": blocked,
            "reason": reason,
        }
    except Exception as e:
        return {
            "success": False, "status": 0, "text": "",
            "stage": "requests", "blocked": True, "reason": str(e),
        }


_HAS_CRAWL4AI = None


def _check_crawl4ai():
    global _HAS_CRAWL4AI
    if _HAS_CRAWL4AI is None:
        try:
            import crawl4ai  # noqa: F401
            _HAS_CRAWL4AI = True
        except ImportError:
            _HAS_CRAWL4AI = False
    return _HAS_CRAWL4AI


async def stage2_playwright(url: str, timeout: int = 30) -> dict:
    from playwright.async_api import async_playwright
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/147.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 720},
            )
            page = await ctx.new_page()
            await page.goto(url, wait_until="networkidle", timeout=timeout * 1000)
            await page.wait_for_timeout(2000)
            title = await page.title()
            text = ""
            for sel in ["article", "main", ".main", "#content", "body"]:
                try:
                    t = await page.inner_text(sel)
                    if t and len(t.strip()) > 100:
                        text = t.strip()
                        break
                except Exception:
                    continue
            if not text:
                text = (await page.inner_text("body") or "").strip()
            await browser.close()
            return {
                "success": bool(text), "status": 200,
                "title": title.strip() if title else "",
                "text": text, "stage": "playwright",
                "blocked": not bool(text), "reason": None if text else "空レスポンス",
            }
    except Exception as e:
        return {
            "success": False, "status": 0, "text": "",
            "stage": "playwright", "blocked": True, "reason": str(e),
        }


async def stage2_crawl4ai(url: str, timeout: int = 30) -> dict:
    if not _check_crawl4ai():
        return await stage2_playwright(url, timeout)

    from crawl4ai import (
        AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode,
        DefaultMarkdownGenerator,
    )
    from crawl4ai.content_filter_strategy import PruningContentFilter

    md_generator = DefaultMarkdownGenerator(
        content_filter=PruningContentFilter(threshold=0.5, threshold_type="dynamic")
    )
    browser_cfg = BrowserConfig(headless=True, verbose=False)
    run_cfg = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        page_timeout=timeout * 1000,
        word_count_threshold=10,
        excluded_tags=["nav", "footer", "header", "aside", "script", "style"],
        markdown_generator=md_generator,
    )
    try:
        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            r = await crawler.arun(url=url, config=run_cfg)
        if r.success:
            text = ""
            md = getattr(r, "markdown", None)
            if md is not None and not isinstance(md, str):
                try:
                    fm = getattr(md, "fit_markdown", None)
                    if fm:
                        text = fm
                except Exception:
                    pass
                if not text:
                    try:
                        rm = getattr(md, "raw_markdown", None)
                        if rm:
                            text = rm
                    except Exception:
                        pass
            if not text:
                text = getattr(r, "fit_markdown", None) or getattr(r, "markdown", None) or r.cleaned_html or r.html or ""
            if not isinstance(text, str):
                text = str(text)
        title = ""
        if r.metadata and isinstance(r.metadata, dict):
            title = r.metadata.get("title", "")
        if not title:
            import re
            m = re.search(r"<title[^>]*>([^<]+)</title>", (r.html or ""), re.I)
            if m:
                title = m.group(1).strip()
        return {
            "success": r.success,
            "status": getattr(r, "status_code", 200) if r.success else 0,
            "title": title,
            "text": text,
            "stage": "crawl4ai",
            "blocked": not r.success,
            "reason": getattr(r, "error_message", None),
        }
    except Exception as e:
        return await stage2_playwright(url, timeout)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="二段構えWeb取得 (requests → Crawl4AI)")
    parser.add_argument("url", help="取得対象URL")
    parser.add_argument("--no-fallback", action="store_true", help="Crawl4AIフォールバックを無効化")
    parser.add_argument("--force-crawl4ai", action="store_true", help="requestsをスキップし最初からCrawl4AIを使用")
    parser.add_argument("--json", action="store_true", help="JSON形式で出力")
    args = parser.parse_args()

    if args.force_crawl4ai:
        result = asyncio.run(stage2_crawl4ai(args.url))
    else:
        result = stage1_requests(args.url)
        if result["blocked"] and not args.no_fallback:
            result = asyncio.run(stage2_crawl4ai(args.url))

    if args.json:
        out = {
            "success": result.get("success", False),
            "stage": result.get("stage", "unknown"),
            "status": result.get("status", 0),
            "title": result.get("title", ""),
            "blocked": result.get("blocked", False),
            "reason": result.get("reason", None),
            "text_length": len(result.get("text", "")),
        }
        write_utf8(json.dumps(out, ensure_ascii=False))
        return

    title = result.get("title", "")
    text = result.get("text", "")
    stage = result.get("stage", "unknown")
    success = result.get("success", False)

    if not success:
        reason = result.get("reason", "不明なエラー")
        write_utf8(f"# 取得失敗（{stage}）")
        write_utf8(f"")
        write_utf8(f"URL: {args.url}")
        write_utf8(f"原因: {reason}")
        sys.exit(1)

    write_utf8(f"# {title}" if title else f"# {args.url}")
    write_utf8(f"")
    write_utf8(f"出典: {args.url}")
    write_utf8(f"取得方式: {stage}")
    write_utf8(f"")
    write_utf8(text)


if __name__ == "__main__":
    main()
