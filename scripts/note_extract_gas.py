#!/usr/bin/env python3
"""
note_extract_gas.py — Note抽出くん（textfromnote2.netlify.app）と同じ経路で note 記事を抽出する

Code適応注記:
- 出典: 本家 PhronisisCore scripts/note_extract_gas.py を移植（2026-11-10、commit eeada168）。
- 依存: requests, beautifulsoup4（playwright 不要）。
- GASプロキシは外部エンドポイント（単一障害点）。env var NOTE_GAS_PROXY_URL で差し替え可。
  プロキシ死亡時は scripts/note_fetch.py（playwright直接）へ降格。詳細は knowledge/code_knowledge/web_research.md。
- Code適応: URL検証を host allowlist（https・note.com / www.note.com）に強化。
  --out はリポジトリ内のみ許可（憲章「ファイル出力はリポジトリ内のみ」）。

画面のアプリは Netlify の静的ページで、HTML取得は Google Apps Script の専用プロキシ、
本文の解析はブラウザ内 JavaScript が行う。本スクリプトは同じプロキシを叩き、
解析だけを Python（BeautifulSoup）に移植した CLI。

使い方:
    python scripts/note_extract_gas.py <note_url>
    python scripts/note_extract_gas.py <note_url> --images
    python scripts/note_extract_gas.py <note_url> --out out.md

オプション:
    --images    画像URLも収集する（アプリの「高機能モード」相当）
    --out PATH  結果を UTF-8 でファイルに書き出す（標準出力は cp932 環境で壊れやすいため推奨）
    --timeout N プロキシ取得のタイムアウト秒（既定40）

環境変数:
    NOTE_GAS_PROXY_URL  GASプロキシURLを差し替える場合に指定

依存: requests, beautifulsoup4
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

DEFAULT_GAS_PROXY_URL = (
    "https://script.google.com/macros/s/"
    "AKfycbwnmHQG90t7sbc4JltzyUJ6VZTADOWvHe-0d6gtyvvCizPHEwHHM-6nCFpP74ydMWbN/exec"
)

REMOVE_SELECTORS = [
    "script", "style", "iframe", "noscript",
    "nav", "footer", "header",
    ".o-noteGlobalHeader", ".o-noteContentHeader",
    ".o-noteAction", ".o-noteShare", ".o-noteTags",
    ".m-noteCreator", ".o-noteComments", ".o-noteRecommend",
    ".o-noteFooter",
    ".p-article__author", "button",
    ".o-noteContentText__download", ".o-noteContentText__copy", ".o-noteSupport",
]

CONTAINER_TAGS = {
    "div", "section", "article", "main", "ul", "ol", "body", "html", "figure",
}


def find_key_deep(obj, key_to_find):
    """JS の findKeyDeep と同じ。最初に見つかった key の値を返す。"""
    if isinstance(obj, dict):
        if key_to_find in obj:
            return obj[key_to_find]
        for value in obj.values():
            found = find_key_deep(value, key_to_find)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = find_key_deep(value, key_to_find)
            if found is not None:
                return found
    return None


def format_date(value):
    if not value:
        return None
    if isinstance(value, str):
        text = value.strip()
        # 2026-01-02T03:04:05... / 2026/01/02 03:04
        m = re.match(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})[T ](\d{1,2}):(\d{1,2})", text)
        if m:
            y, mo, d, h, mi = m.groups()
            return f"{y}/{int(mo):02d}/{int(d):02d} {int(h):02d}:{int(mi):02d}"
        m = re.match(r"(\d{4})年(\d{1,2})月(\d{1,2})日\s*(\d{1,2}):(\d{1,2})", text)
        if m:
            y, mo, d, h, mi = m.groups()
            return f"{y}/{int(mo):02d}/{int(d):02d} {int(h):02d}:{int(mi):02d}"
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.strftime("%Y/%m/%d %H:%M")
    except Exception:
        return None


def clean_dom(root):
    for selector in REMOVE_SELECTORS:
        for el in root.select(selector):
            if el.find_parent("blockquote") is None:
                el.decompose()


def text_recursive(node):
    out = []
    for child in node.children:
        if isinstance(child, NavigableString):
            out.append(str(child))
        elif isinstance(child, Tag):
            tag = child.name.lower()
            if tag == "br":
                out.append("\n")
            else:
                out.append(text_recursive(child))
                if tag in ("p", "div", "li", "h1", "h2", "h3", "section", "footer"):
                    out.append("\n")
    return "".join(out)


def normalize_lines(text):
    lines = []
    for line in text.split("\n"):
        line = re.sub(r"[\u00a0\u3000]+", " ", line).strip()
        if line:
            lines.append(line)
    return lines


def to_quote(text):
    return "\n".join("> " + line for line in normalize_lines(text))


def extract_content(container, collect_images, images=None):
    parts = []
    images = images if images is not None else []
    counter = {"n": len(images)}

    def walk(node):
        if not isinstance(node, Tag):
            return
        tag = node.name.lower()

        # BeautifulSoup のルート（[document]）はそのまま子を走査する
        if tag.startswith("["):
            for child in node.children:
                walk(child)
            return

        if tag == "figure" or (tag == "img" and node.find_parent("figure") is None):
            img = node if tag == "img" else node.find("img")
            if img is not None and node.find("iframe") is None:
                if collect_images:
                    src = img.get("data-src") or img.get("src")
                    if src and not src.startswith("data:"):
                        counter["n"] += 1
                        images.append(src)
                        caption = ""
                        figcaption = node.find("figcaption") if tag == "figure" else None
                        if figcaption is not None:
                            caption = text_recursive(figcaption).strip()
                        elif img.get("alt"):
                            caption = (img.get("alt") or "").strip()
                        if not caption:
                            caption = f"画像{counter['n']}"
                        parts.append(f"\n※※画像{counter['n']}:({caption})")
                else:
                    counter["n"] += 1
                    parts.append(f"\n※※画像{counter['n']}")
                return

            if tag == "figure":
                blockquote = node.find("blockquote")
                if blockquote is not None:
                    body = text_recursive(blockquote).strip()
                    source_el = node.find("figcaption") or node.find("cite")
                    source = text_recursive(source_el).strip() if source_el is not None else ""
                    combined = body
                    if source:
                        prefix = "" if re.match(r"^[-—ー]", source) else "— "
                        combined += "\n" + prefix + source
                    if combined.strip():
                        parts.append("\n" + to_quote(combined))
                    return

        if tag == "blockquote":
            body = text_recursive(node).strip()
            nxt = node.find_next_sibling()
            source = ""
            if nxt is not None and nxt.name in ("cite", "figcaption"):
                source = text_recursive(nxt).strip()
                nxt.decompose()
            combined = body
            if source:
                prefix = "" if re.match(r"^[-—ー]", source) else "— "
                combined += "\n" + prefix + source
            if combined.strip():
                parts.append("\n" + to_quote(combined))
            return

        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(tag[1])
            parts.append("\n" + "#" * level + " " + node.get_text().strip())
            return

        if tag in ("p", "li"):
            text = text_recursive(node).strip()
            if text:
                processed = "\n".join(
                    re.sub(r"[\u00a0\u3000]+", " ", line).strip()
                    for line in text.split("\n")
                )
                if tag == "li":
                    parts.append("・" + processed)
                else:
                    parts.append(processed)
            return

        if tag in CONTAINER_TAGS or "note" in tag:
            for child in node.children:
                walk(child)

    walk(container)
    return "\n\n".join(parts), images


def parse_html(html, source_url, collect_images):
    soup = BeautifulSoup(html, "html.parser")
    clean_url = source_url.split("?")[0]

    title = ""
    author = "作者不明"
    raw_date = None
    hydration = None

    next_data = soup.find("script", id="__NEXT_DATA__")
    if next_data is not None and next_data.string:
        try:
            data = json.loads(next_data.string)
            hydration = find_key_deep(data, "note")
            if isinstance(hydration, dict):
                title = hydration.get("name") or ""
                user = hydration.get("user") or {}
                if isinstance(user, dict) and user.get("nickname"):
                    author = user["nickname"]
                raw_date = hydration.get("publishAt") or raw_date
        except Exception:
            pass

    if not title:
        og = soup.find("meta", attrs={"property": "og:title"})
        og_title = (og.get("content") if og else None) or (soup.title.string if soup.title else "") or ""
        parts = [s.strip() for s in og_title.split("｜")]
        if parts and parts[-1] == "note":
            parts.pop()
        if len(parts) >= 2:
            possible_author = parts.pop()
            if author == "作者不明":
                author = possible_author
            title = "｜".join(parts)
        else:
            title = "｜".join(parts)

    if author == "作者不明":
        for attrs in ({"name": "twitter:creator"}, {"name": "author"}):
            meta = soup.find("meta", attrs=attrs)
            if meta and meta.get("content"):
                author = meta["content"]
                break

    if author == "作者不明":
        for selector in (".o-noteCreator__name", ".m-noteCreator__name",
                         ".o-noteContentHeader__name", 'a[href^="/users/"]'):
            el = soup.select_one(selector)
            if el is not None:
                author = el.get_text(strip=True)
                break

    if not raw_date:
        area = soup.select_one(".o-noteContentHeader") or soup.body or soup
        header = area.get_text(" ", strip=True)[:2000]
        m = re.search(r"(\d{4})/(\d{1,2})/(\d{1,2})\s+(\d{1,2}):(\d{1,2})", header)
        if m:
            raw_date = m.group(0)
        else:
            m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日\s*(\d{1,2}):(\d{1,2})", header)
            if m:
                raw_date = m.group(0)

    published = format_date(raw_date) or "不明"
    current = datetime.now().strftime("%Y/%m/%d %H:%M")

    images = []
    if collect_images:
        og_image = soup.find("meta", attrs={"property": "og:image"})
        if og_image is not None:
            src = og_image.get("content")
            if src and "assets/img/common/" not in src:
                images.append(src)

    if collect_images and isinstance(hydration, dict) and (hydration.get("bodyHtml") or hydration.get("body")):
        body_html = hydration.get("bodyHtml") or hydration.get("body")
        container = BeautifulSoup(body_html, "html.parser")
        method = "Hydration"
    else:
        container = (
            soup.select_one('[data-name="body"]')
            or soup.select_one(".note-common-styles")
            or soup.select_one(".p-article__content")
            or soup.select_one("article")
            or soup.select_one("#main")
        )
        if container is None:
            container = BeautifulSoup(str(soup.body), "html.parser") if soup.body else soup
            method = "Body Scan"
        else:
            method = "DOM"

    clean_dom(container)
    body, images = extract_content(container, collect_images, images)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    method += " (高機能 / 独立基地経由)" if collect_images else " (軽量 / 独立基地経由)"

    text = (
        f"タイトル:{title}\n"
        f"作者:{author}\n"
        f"投稿日時:{published}\n"
        f"現在日時:{current}\n"
        f"掲載URL: {clean_url}\n\n"
        f"{body}"
    )
    return {"text": text, "method": method, "images": images}


def fetch_via_gas(url, proxy, timeout):
    resp = requests.get(proxy, params={"url": url}, timeout=timeout)
    resp.raise_for_status()
    try:
        data = resp.json()
    except Exception as exc:
        raise RuntimeError(f"プロキシの応答がJSONではありません: {exc}") from exc
    if data.get("error"):
        raise RuntimeError(f"APIエラー: {data['error']}")
    status = data.get("status")
    if status is not None and int(status) != 200:
        raise RuntimeError(f"対象ページがエラーステータス({status})を返しました")
    html = data.get("contents") or ""
    if len(html) <= 1000:
        raise RuntimeError("取得データが異常に短いです")
    return html


def write_output(text, out_path):
    data = text.encode("utf-8")
    if out_path:
        with open(out_path, "wb") as f:
            f.write(data)
            if not data.endswith(b"\n"):
                f.write(b"\n")
    else:
        sys.stdout.buffer.write(data)
        if not data.endswith(b"\n"):
            sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()


def main(argv=None):
    parser = argparse.ArgumentParser(description="note記事をGASプロキシ経由で抽出する")
    parser.add_argument("url", help="https://note.com/... の記事URL")
    parser.add_argument("--images", action="store_true", help="画像URLも収集する（高機能モード）")
    parser.add_argument("--out", help="UTF-8で書き出すファイルパス")
    parser.add_argument("--timeout", type=int, default=40, help="プロキシ取得のタイムアウト秒")
    args = parser.parse_args(argv)

    target = urlparse(args.url)
    if target.scheme != "https" or target.hostname not in ("note.com", "www.note.com"):
        print("ERROR: note.com の https URL ではありません（host allowlist）", file=sys.stderr)
        return 2

    if args.out:
        root = Path(__file__).resolve().parents[1]
        try:
            Path(args.out).resolve().relative_to(root)
        except ValueError:
            print(f"ERROR: --out はリポジトリ内のみ許可します: {args.out}", file=sys.stderr)
            return 2

    proxy = os.environ.get("NOTE_GAS_PROXY_URL", DEFAULT_GAS_PROXY_URL)
    try:
        html = fetch_via_gas(args.url, proxy, args.timeout)
        result = parse_html(html, args.url, args.images)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    write_output(result["text"], args.out)
    print(f"[method] {result['method']}", file=sys.stderr)
    if args.images:
        print(f"[images] {len(result['images'])}", file=sys.stderr)
        for i, src in enumerate(result["images"], 1):
            print(f"  {i}: {src}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
