"""DSH（DeepSeek Harness）の最新応答確認スクリプト

Code適応注記:
- 出典: 本家 PhronisisCore scripts/dsh_check.py から移植（2026-11-11）。ロジック不変。
- 詳細は knowledge/code_knowledge/dsh.md を参照。

PhronisisDSH の Web UI（127.0.0.1:3080）で動作している DKai（DSH側カイ）の最新応答を、
UTF-8ファイル（scratch/dsh_reply.txt）に保存して読み取る。

使い方:
  python scripts/dsh_check.py [--session "セッション名の部分文字列"] [--out "出力ファイル"]

注意:
  - DKaiとの会話は「送信（dsh_send.py）→ 応答の確認（本スクリプト）」で1往復が完了する。
    送信したら必ず本スクリプトで相手の応答を読むこと（完了 = 相手の応答の確認）
  - 保存されたファイルを Read で読むことが完了判定。state 表示は参考（ページ全体の
    キーワード走査であり、生成中でもサイドバー表示によっては誤る場合がある）
  - 相手がAsk the userで質問を投げている場合は scripts/dsh_answer.py を使用

依存: playwright（pip install playwright / python -m playwright install chromium）
"""

import argparse
import sys

from dsh_common import open_session, save_page_text, report_status, build_url, check_ledger


def main():
    parser = argparse.ArgumentParser(description="DSHの最新応答を確認")
    parser.add_argument("--uuid", default="", help="開くセッションのUUID（推奨。--session より優先）")
    parser.add_argument("--session", "-s", default="", help="開くセッション名の部分文字列（互換用）")
    parser.add_argument("--workspace", default="", help="追加済みのワークスペース名（例: PhronisisDSH）")
    parser.add_argument("--allow-unlisted", action="store_true", help="台帳外のUUIDを発見手順として許可")
    parser.add_argument("--out", "-o", default="scratch/dsh_reply.txt", help="出力ファイル（UTF-8）")
    parser.add_argument("--url", default="http://127.0.0.1:3080", help="DSH Web UIのURL")
    args = parser.parse_args()

    check_ledger(args.uuid, args.allow_unlisted)

    import asyncio
    from playwright.async_api import async_playwright

    async def run():
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            url = build_url(args.url)
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)

            try:
                await open_session(page, session_keyword=args.session,
                                   session_uuid=args.uuid, workspace=args.workspace)
            except LookupError as e:
                print(f"確認を中止しました: {e}", file=sys.stderr)
                await browser.close()
                sys.exit(1)

            await page.wait_for_timeout(2500)

            # 全文をUTF-8ファイルに保存（cp932回避のためコンソールに出さない）
            text = await save_page_text(page, args.out)

            # state は参考表示（3種すべて参考。完了判定は本文をReadで読むこと）
            print(f"state: {report_status(text)}", file=sys.stderr)
            print(f"saved: {args.out}", file=sys.stderr)
            print("完了判定は保存された本文をReadで読むこと。state表示は参考", file=sys.stderr)

            await browser.close()

    asyncio.run(run())


if __name__ == "__main__":
    main()
