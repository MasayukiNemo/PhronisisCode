#!/usr/bin/env python3
"""
note_fetch.py — note.com 記事をヘッドレス Chromium で取得してMarkdown出力

Code適応注記:
- 本家 PhronisisCore scripts/note_fetch.py から移植（2026-11-10）。ロジック不変。
- web_fetch.py で代用可能な場合が多い（保険的位置づけ）。詳細は knowledge/code_knowledge/web_research.md。

使い方:
  python scripts/note_fetch.py <note_url>

依存: playwright（pip install playwright）
初回のみ: python -m playwright install chromium
"""

import sys, asyncio, json, re

def write_utf8(text):
    sys.stdout.buffer.write(text.encode('utf-8'))
    sys.stdout.buffer.write(b'\n')
    sys.stdout.buffer.flush()

async def fetch_note(url: str) -> dict:
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
        )
        page = await ctx.new_page()
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)

        title = await page.title()
        content_text = await page.inner_text("article") or ""
        # Get HTML for more structured extraction
        content_html = await page.inner_html("article") or ""

        # Extract metadata
        meta = {}
        meta_els = await page.query_selector_all('meta[name]')
        for el in meta_els:
            name = await el.get_attribute("name")
            content = await el.get_attribute("content")
            if name and content:
                meta[name] = content

        await browser.close()

    return {
        "url": url,
        "title": title.strip() if title else "",
        "text": content_text.strip(),
        "html": content_html,
        "meta": meta,
    }

def main():
    if len(sys.argv) < 2:
        write_utf8("Usage: python scripts/note_fetch.py <note_url>")
        sys.exit(1)

    url = sys.argv[1]
    if not url.startswith("https://note.com/"):
        write_utf8("ERROR: URL must start with https://note.com/")
        sys.exit(1)

    try:
        result = asyncio.run(fetch_note(url))
    except Exception as e:
        write_utf8(f"ERROR: {e}")
        sys.exit(1)

    write_utf8(f"# {result['title']}")
    write_utf8(f"")
    write_utf8(f"出典: {result['url']}")
    write_utf8(f"")
    write_utf8(result["text"])

if __name__ == "__main__":
    main()
