"""DSH（DeepSeek Harness）の Ask the user 質問への回答スクリプト

Code適応注記:
- 出典: 本家 PhronisisCore scripts/dsh_answer.py から移植（2026-11-11）。ロジック不変。
- 詳細は knowledge/code_knowledge/dsh.md を参照。

PhronisisDSH の Web UI（127.0.0.1:3080）で、DSH側Kaiが「Ask the user」で択一質問を
投げている場合に、選択肢をクリックして回答（提交）する。

使い方:
  python scripts/dsh_answer.py --option "修正する" [--session "セッション名の部分文字列"]

  --option は選択肢に含まれる文字列（例: "修正する"）。該当する選択肢をクリックして送信する。
  送信確認: クリック後に回答が反映されたことを観測してから報告する。

注意:
  - 向こうのKaiがAsk the userで質問提示中は、通常のテキストエリアが出ない。
    このスクリプトで選択肢に回答してから、次の会話を続けること
  - 根本さんの判断が「この選択肢で進め」という形で既に決まっている場合に使用する

依存: playwright（pip install playwright / python -m playwright install chromium）
"""

import argparse
import sys

from dsh_common import open_session, build_url


async def _find_submit_button(page):
    """提交ボタンを探す。なければ None"""
    buttons = await page.query_selector_all("button")
    for el in buttons:
        try:
            txt = (await el.inner_text()).strip()
            if txt == "提交":
                return el
        except Exception:
            pass
    return None


async def _answer_accepted(page, submit_el, timeout_ms=5000):
    """回答確認: クリック前に取得した提交ボタン要素が消えた（無効化された）ことを観測する。

    - submit_el はクリック前に取得した要素。これを基準に「消えたか」を判定する。
    - クリック前に提交ボタンの存在を確認しておく（最初から存在しない場合は確認対象外）
    - 回答が受理されると Ask the user の選択肢UI（提交ボタン含む）が消えるはず。
      その消滅を観測してから「回答を送信しました」と報告する。
    """
    import time
    start = time.time()
    while time.time() - start < timeout_ms / 1000:
        try:
            # クリック前に取得した要素がページから消えた（detached）か確認
            detached = await submit_el.evaluate("e => !e.isConnected")
            if detached:
                return True
            # 無効化（disabled）された場合も受理とみなす
            disabled = await submit_el.is_disabled()
            if disabled:
                return True
        except Exception:
            pass
        await page.wait_for_timeout(500)
    return False


def main():
    parser = argparse.ArgumentParser(description="DSHのAsk the user質問に回答")
    parser.add_argument("--option", "-o", required=True, help="選択する選択肢の部分文字列（例: 修正する）")
    parser.add_argument("--session", "-s", default="", help="開くセッション名の部分文字列（省略時は最初のセッション）")
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
            await page.wait_for_timeout(2000)

            try:
                await open_session(page, session_keyword=args.session)
            except LookupError as e:
                print(f"回答を中止しました: {e}", file=sys.stderr)
                await browser.close()
                sys.exit(1)

            await page.wait_for_timeout(2500)

            # 選択肢を探してクリック
            clickables = await page.query_selector_all("button, [role=button], [role=option], [role=radio], label")
            clicked_opt = False
            for el in clickables:
                try:
                    txt = (await el.inner_text()).strip()
                    if args.option in txt:
                        await el.click()
                        clicked_opt = True
                        break
                except Exception:
                    pass
            if not clicked_opt:
                print("警告: 選択肢が見つかりません。Ask the user質問が無い可能性があります", file=sys.stderr)
                await browser.close()
                return

            await page.wait_for_timeout(1000)

            # 提交ボタンの存在をクリック前に確認する（回答受理の観測基準にする）
            submit_el = await _find_submit_button(page)
            if submit_el is None:
                print("警告: 提交ボタンが見つかりません。Ask the user質問が無い可能性があります", file=sys.stderr)
                await browser.close()
                return

            # 提交ボタンをクリック
            clicked_submit = False
            try:
                await submit_el.click()
                clicked_submit = True
            except Exception:
                pass

            # 回答確認: クリック前に存在した提交ボタンが消えた（無効化された）ことを観測してから報告する
            # （選択肢の文言はクリック前から存在するため、それを確認に使わない）
            accepted = await _answer_accepted(page, submit_el)
            if clicked_opt and clicked_submit and accepted:
                print("回答を送信しました（提交ボタンの消滅/無効化を確認）", file=sys.stderr)
            else:
                print(f"結果: option={clicked_opt} submit={clicked_submit} accepted={accepted}", file=sys.stderr)
            await browser.close()

    asyncio.run(run())


if __name__ == "__main__":
    main()
