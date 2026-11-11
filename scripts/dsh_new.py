"""DSHの新規セッション（draft）を作り、そのUUIDを標準出力に出す。

使い方:
  python scripts/dsh_new.py [--workspace PhronisisDSH]

作っただけでは送信しない。送信は dsh_send.py --uuid <uuid> で行う。
（--new 付き送信は、DSHのdraft設計により旧draftへ送ることがあるため、
  作成と送信を分ける）
"""

import argparse
import sys

from dsh_common import build_url, dismiss_modals, switch_workspace, _click_new_session, list_sessions


def main():
    parser = argparse.ArgumentParser(description="DSHの新規セッションを作りUUIDを出す")
    parser.add_argument("--workspace", default="", help="追加済みのワークスペース名（例: PhronisisDSH）")
    parser.add_argument("--url", default="http://127.0.0.1:3080", help="DSH Web UIのURL")
    args = parser.parse_args()

    import asyncio
    from playwright.async_api import async_playwright

    async def run():
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(build_url(args.url), wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2500)
            await dismiss_modals(page)
            if args.workspace:
                await switch_workspace(page, args.workspace)
            await _click_new_session(page)
            sessions = await list_sessions(page)
            await browser.close()
        for s in sessions:
            if s["selected"] and s["uuid"]:
                sys.stdout.buffer.write((s["uuid"] + "\n").encode("utf-8"))
                sys.stdout.buffer.flush()
                return 0
        print("エラー: 新規セッションのUUIDを特定できませんでした", file=sys.stderr)
        return 1

    sys.exit(asyncio.run(run()))


if __name__ == "__main__":
    main()
