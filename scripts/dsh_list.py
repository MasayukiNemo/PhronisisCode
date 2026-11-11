"""DSHのセッション一覧（UUID／タイトル／時刻／選択状態）を出す。

使い方:
  python scripts/dsh_list.py [--workspace PhronisisDSH] [--json] [--out PATH]

UUID は data-row-key="session:session-<uuid>" から抽出する。
DSHの内部属性なので、版上がりで取れなくなったら止めて報告する（名前一致に逃げない）。
"""

import argparse
import json
import sys

from dsh_common import build_url, dismiss_modals, switch_workspace, list_sessions


def main():
    parser = argparse.ArgumentParser(description="DSHのセッション一覧")
    parser.add_argument("--workspace", default="", help="追加済みのワークスペース名（例: PhronisisDSH）")
    parser.add_argument("--json", action="store_true", help="JSONで出力")
    parser.add_argument("--out", default="", help="UTF-8でファイル出力")
    parser.add_argument("--url", default="http://127.0.0.1:3080", help="DSH Web UIのURL")
    args = parser.parse_args()

    import asyncio
    from playwright.async_api import async_playwright

    async def run():
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            url = build_url(args.url)
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2500)
            await dismiss_modals(page)
            if args.workspace:
                await switch_workspace(page, args.workspace)
            sessions = await list_sessions(page)
            await browser.close()

        no_uuid = [s for s in sessions if not s["uuid"]]
        if args.json:
            text = json.dumps(sessions, ensure_ascii=False, indent=2) + "\n"
        else:
            lines = ["UUID\tTITLE\tTIME\tSELECTED"]
            for s in sessions:
                lines.append(
                    f"{s['uuid'] or '(uuid?)'}\t{s['title']}\t{s['time']}\t{'*' if s['selected'] else ''}"
                )
            text = "\n".join(lines) + "\n"
        if no_uuid:
            text += f"WARN: UUIDを抽出できない行が {len(no_uuid)} 件あります（DSHの内部属性が変わった可能性）。\n"
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"saved: {args.out}", file=sys.stderr)
        else:
            sys.stdout.buffer.write(text.encode("utf-8"))
            sys.stdout.buffer.flush()
        return 0 if not no_uuid else 2

    sys.exit(asyncio.run(run()))


if __name__ == "__main__":
    main()
