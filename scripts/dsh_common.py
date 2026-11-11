"""DSH（DeepSeek Harness）操作の共通処理

Code適応注記:
- 出典: 本家 PhronisisCore scripts/dsh_common.py から移植（2026-11-11）。
- トークン検出を現行ランチャー（%LOCALAPPDATA%\\PhronisisDSH\\start.out*）に追加。
- 詳細は knowledge/code_knowledge/dsh.md を参照。

dsh_send.py / dsh_check.py / dsh_answer.py で共通利用するセッションオープン処理を集約する。
（各スクリプトでコピペしない。修正はここだけで済むようにする）

バージョン対応（2026-09-23追記）:
- このリポジトリを触る端末によって DSH のバージョンが異なる。
  - LAPTOP-VO3C74SH（常時稼働PC）: DSH v0.1.0-rc.6 → 新規作成ボタンは「新会话」（中国語）
  - DESKTOP-BTNIQ5L（自宅ノートPC）: DSH v0.1.5-rc.3 → 新規作成ボタンは「New Session」（英語）
- 両バージョンで動くよう、新規作成ボタンの文言は「新会话」「New Session」の両方を判定する。
- セッション行のクラスは両バージョンとも `[class*="sessionRow"]` で共通（ハッシュ付きCSS Modules）。
"""

import sys
import os
import re
import glob


def find_token():
    """DSH Web UI のアクセストークンを起動ログから検出する。

    DSH v0.1.5+ は Web UI がトークン認証必須。トークンは起動時に stdout へ
    「dsh web: http://127.0.0.1:3080/?token=...」として出力される。

    Code適応（2026-11-11）: 現行ランチャー start_dsh.cmd は
    %LOCALAPPDATA%\\PhronisisDSH\\start.out に出す（毎回 .prev にローテーション）。
    そこを正とし、旧パス（%TEMP%）も互換のため走査する。
    """
    local = os.environ.get("LOCALAPPDATA", "")
    candidates = []
    if local:
        candidates += [
            os.path.join(local, "PhronisisDSH", "start.out"),
            os.path.join(local, "PhronisisDSH", "start.out.prev"),
            os.path.join(local, "PhronisisDSH", "start.log"),
        ]
    candidates += glob.glob(os.path.join(os.environ.get("TEMP", ""), "dsh_out*.txt"))
    candidates += [os.path.join(os.environ.get("TEMP", ""), "dsh_start.log")]
    # 存在しないパスを除外（getmtimeがFileNotFoundErrorで落ちるため）
    candidates = [p for p in candidates if os.path.exists(p)]
    # 更新時刻の新しい順
    candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    for p in candidates:
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    m = re.search(r"token=([A-Za-z0-9_-]+)", line)
                    if m:
                        return m.group(1)
        except Exception:
            pass
    return None


def build_url(base_url="http://127.0.0.1:3080"):
    """DSH Web UI のアクセスURLを返す。トークン付き。

    引数の base_url に既に token= が含まれていればそのまま使う。
    無ければ起動ログからトークンを検出して付与する。
    トークンが見つからない場合はトークンなしURLを返す（旧バージョン互換）。
    """
    if "token=" in base_url:
        return base_url
    token = find_token()
    if token:
        sep = "&" if "?" in base_url else "?"
        return f"{base_url}{sep}token={token}"
    return base_url


async def _wait_for_session_rows(page, timeout_s=15.0, poll_s=0.5):
    """セッション行が表示されるまでポーリング待機する。

    旧バージョンでは page.goto 直後でも表示されるが、新バージョン（0.1.5+）では
    レンダリングが遅延することがある。セッション行が現れるまで待ってから操作する。
    """
    import time
    start = time.time()
    while time.time() - start < timeout_s:
        items = await page.query_selector_all('[class*="sessionRow"]')
        if items:
            return items
        await page.wait_for_timeout(poll_s * 1000)
    return await page.query_selector_all('[class*="sessionRow"]')


def _is_new_session_item(txt):
    """新規作成ボタン（セッションではない）か判定。両バージョンの文言に対応"""
    t = txt.strip()
    return "新会话" in t or "New Session" in t


async def dismiss_modals(page, timeout_s=6.0):
    """起動直後に出るモーダル（プレビュー通知など）を閉じる。

    DSH 0.2 のプレビュー通知が role=dialog + mask で操作を遮るため、
    open_session の前に閉じる。モーダルの出現が遅れることがあるので待つ。
    """
    import time
    start = time.time()
    while time.time() - start < timeout_s:
        try:
            dlg = await page.query_selector('[role="dialog"]')
            if dlg:
                for label in ("続ける", "閉じる", "OK", "了解"):
                    btns = await dlg.query_selector_all("button")
                    for el in btns:
                        try:
                            if (await el.inner_text()).strip() == label:
                                await el.click(timeout=3000)
                                await page.wait_for_timeout(700)
                                return True
                        except Exception:
                            pass
        except Exception:
            pass
        await page.wait_for_timeout(400)
    return False


async def open_session(page, session_keyword="", create_new=False):
    """DSHのセッションを開く。

    - session_keyword が指定されていれば、その部分文字列を含むセッションを開く
      （複数マッチ時は先頭を選択。DOM順＝表示順）
    - 指定セッションが見つからない場合はエラー（新規作成はしない。誤送信防止）
    - session_keyword が空なら、最初のセッション項目（新規作成ボタンを除く）を開く
    - セッションが0件の場合はエラー（新規作成は --new 明示時のみ）
    - create_new=True なら新規作成ボタンをクリックして新規セッションを作る
    """
    # 起動直後のモーダル（プレビュー通知）がクリックを遮るので先に閉じる
    await dismiss_modals(page)

    if create_new:
        await _click_new_session(page)
        return

    # セッション行が表示されるまで待機（新バージョンのレンダリング遅延対策）
    items = await _wait_for_session_rows(page)

    if session_keyword:
        for it in items:
            try:
                txt = (await it.inner_text()).strip()
                if _is_new_session_item(txt):
                    continue
                if session_keyword in txt:
                    await it.click()
                    return
            except Exception:
                pass
        # 指定セッションが見つからない。黙って新規作成せず、失敗で止める（誤送信防止）
        print(f"エラー: セッション '{session_keyword}' が見つかりません。", file=sys.stderr)
        print("セッション名を確認してください（サイドバーのセッション一覧を参照）", file=sys.stderr)
        raise LookupError(f"session not found: {session_keyword}")

    # キーワード未指定: 最初のセッション項目を開く（新規作成ボタンを除外）
    for it in items:
        try:
            txt = (await it.inner_text()).strip()
            if txt and not _is_new_session_item(txt) and txt.splitlines()[0].strip():
                await it.click()
                return
        except Exception:
            pass
    # セッションが0件: 黙って新規作成せず、失敗で止める（--new 明示時のみ新規作成）
    print("エラー: 開くセッションがありません。", file=sys.stderr)
    print("セッション名を指定するか、--new を明示してください", file=sys.stderr)
    raise LookupError("no session available")


async def _click_new_session(page):
    """新規作成ボタンをクリック。両バージョンの文言（新会话 / New Session）に対応"""
    buttons = await page.query_selector_all("button")
    for b in buttons:
        try:
            txt = (await b.inner_text()).strip()
            if txt == "新会话" or txt == "New Session" or "新会话" in txt or "New Session" in txt:
                await b.click()
                return
        except Exception:
            pass
    # ボタンで見つからない場合はセッション行（New Session項目）を直接クリック
    items = await page.query_selector_all('[class*="sessionRow"]')
    for it in items:
        try:
            txt = (await it.inner_text()).strip()
            if _is_new_session_item(txt):
                await it.click()
                return
        except Exception:
            pass


async def save_page_text(page, out_path):
    """ページ全体のテキストをUTF-8ファイルに保存（cp932対策）"""
    text = await page.inner_text("body")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    return text


def report_status(text):
    """状態表示（参考用）。完了判定は本文を読むこと。3種すべて参考扱い"""
    if "等待回答" in text or "等待" in text:
        return "awaiting-answer(参考)"
    if "进行中" in text or "正在生成" in text:
        return "running(参考)"
    return "idle(参考)"