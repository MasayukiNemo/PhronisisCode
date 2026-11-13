"""DSH（DeepSeek Harness）へのメッセージ送信スクリプト

Code適応注記:
- 出典: 本家 PhronisisCore scripts/dsh_send.py から移植（2026-11-11）。ロジック不変。
- 詳細は knowledge/code_knowledge/dsh.md を参照。

PhronisisDSH の Web UI（127.0.0.1:3080）で動作している DKai（DSH側カイ）にメッセージを送る。

使い方:
  python scripts/dsh_send.py --message "本文" [--session "セッション名の部分文字列"] [--new]

注意:
  - DSHのKaiへの伝達は「ファイルを置く」だけでは完了しない。このスクリプトでセッションに
    実際にメッセージを送ること（=話しかけること）までがセッションの開始である
  - 送信後は必ず scripts/dsh_check.py で相手の応答を確認すること（完了 = 相手の応答の確認）
  - 送信確認: Enter押下後に、自分のメッセージが会話領域に現れたことを観測してから報告する
  - --message を省略すると標準入力から読む（長文メッセージ向け）

依存: playwright（pip install playwright / python -m playwright install chromium）
"""

import argparse
import sys

from dsh_common import open_session, build_url, check_ledger, CARD_TEXT


def _read_message(args):
    """メッセージ本文を取得（引数 or 標準入力）"""
    if args.message:
        return args.message
    # 標準入力から読む（Windows cp932 対策のため、stderr に UTF-8 で書く）
    print("メッセージを入力してください（Ctrl+Z + Enter で終了）:", file=sys.stderr)
    return sys.stdin.read()


async def _message_appeared(page, message, input_locator, timeout_ms=5000):
    """送信確認: 入力欄がクリアされ、かつメッセージが会話領域に現れたかを観測する。

    - 入力欄にメッセージが残っている = Enterが効かなかった = 未送信
    - 入力欄が空になり、メッセージ本文がページ（会話領域）に現れた = 送信成功
    - textarea と contenteditable の両方に対応
    """
    import time
    start = time.time()
    preview = message.strip()[:40]
    while time.time() - start < timeout_ms / 1000:
        try:
            area_value = await input_locator.inner_text()
            area_empty = not area_value.strip()
            text = await page.inner_text("body")
            message_shown = preview in text
            if area_empty and message_shown:
                return True
        except Exception:
            pass
        await page.wait_for_timeout(500)
    return False


def main():
    parser = argparse.ArgumentParser(description="DSHへメッセージを送信")
    parser.add_argument("--message", "-m", help="送信するメッセージ（省略時は標準入力）")
    parser.add_argument("--uuid", default="", help="開くセッションのUUID（推奨。--session より優先）")
    parser.add_argument("--session", "-s", default="", help="開くセッション名の部分文字列（互換用）")
    parser.add_argument("--workspace", default="", help="追加済みのワークスペース名（例: PhronisisDSH）")
    parser.add_argument("--allow-unlisted", action="store_true", help="台帳外のUUIDを発見手順として許可")
    parser.add_argument("--new", action="store_true", help="新規セッションを作成して送信")
    parser.add_argument("--card", action="store_true", help="セッション開始時に接続カード（v0.2）を前置する")
    parser.add_argument("--url", default="http://127.0.0.1:3080", help="DSH Web UIのURL")
    args = parser.parse_args()

    check_ledger(args.uuid, args.allow_unlisted)
    message = _read_message(args)
    if args.card:
        message = CARD_TEXT + "\n---\n\n" + message
    if not message.strip():
        print("エラー: メッセージが空です", file=sys.stderr)
        sys.exit(1)

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
                await open_session(page, session_keyword=args.session, create_new=args.new,
                                   session_uuid=args.uuid, workspace=args.workspace)
            except LookupError as e:
                print(f"送信を中止しました: {e}", file=sys.stderr)
                await browser.close()
                sys.exit(1)

            await page.wait_for_timeout(2000)

            # 入力欄を取得（textarea / contenteditable 両対応。DSH v0.1.5+ は contenteditable）
            ta = page.locator("textarea, [contenteditable=true], [contenteditable='']").first
            await ta.wait_for(state="visible", timeout=10000)
            await ta.click()
            await ta.fill(message)
            await page.wait_for_timeout(500)
            await ta.press("Enter")

            # 送信確認: テキストエリアがクリアされ、かつ自分のメッセージが会話領域に現れたことを
            # 観測してから報告する（Enterが効かず残っていたら未送信として警告）
            appeared = await _message_appeared(page, message, ta)
            if appeared:
                print("送信しました（テキストエリアクリア+会話領域で確認）。応答は scripts/dsh_check.py で確認してください", file=sys.stderr)
            else:
                print("警告: 送信を確認できませんでした（テキストエリアに残っている可能性）。再送または手動確認してください", file=sys.stderr)
            await browser.close()

    asyncio.run(run())


if __name__ == "__main__":
    main()
