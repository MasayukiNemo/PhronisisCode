#!/usr/bin/env python3
"""
quiz_game.py — Geminiおまかせクイズゲーム（CLI対話式）

agy経由Geminiにテーマ・出題・解説を任せる4択クイズ。標準ライブラリのみ。
conduct準拠: ask前にquota確認、7%以下は停止、ask結果はtasks logに記録する運用。

遊び方:
    python scripts/quiz_game.py [--num 5]
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AGY_QUERY = REPO_ROOT / "scripts" / "agy_query.py"
QUOTA_STOP_THRESHOLD = 7
DEFAULT_NUM = 5


def safe_console():
    """cp932コンソールで落ちないよう置換出力にする（表示崩れと実害を分離）。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def ask_quota():
    """残量JSONを返す。取得不能時は空辞書。"""
    try:
        proc = subprocess.run(
            [sys.executable, str(AGY_QUERY), "quota"],
            capture_output=True, timeout=120, cwd=str(REPO_ROOT))
    except (OSError, subprocess.SubprocessError):
        return {}
    try:
        data = json.loads(proc.stdout.decode("utf-8", errors="replace"))
        return data if isinstance(data, dict) else {}
    except ValueError:
        return {}


def ask_gemini(prompt, timeout=180):
    """agy askを1回投げる。戻り: (ok, text)。"""
    try:
        proc = subprocess.run(
            [sys.executable, str(AGY_QUERY), "ask", prompt, "--timeout", str(timeout)],
            capture_output=True, timeout=timeout + 30, cwd=str(REPO_ROOT))
    except (OSError, subprocess.SubprocessError) as exc:
        return False, "ask実行に失敗: {}".format(exc)
    text = proc.stdout.decode("utf-8", errors="replace").strip()
    if proc.returncode != 0 or not text:
        err = proc.stderr.decode("utf-8", errors="replace").strip()[:300] or text[:300]
        return False, err or "応答なし"
    return True, text


def extract_json(text):
    """フェンス除去してJSONを読む。失敗時は例外を投げる（捏造しない）。"""
    body = text.strip()
    if body.startswith("```"):
        lines = body.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        body = "\n".join(lines)
    return json.loads(body)


def valid_question(item):
    """1問分の構造検証。通過した正規化問を返す。ダメならNone。"""
    if not isinstance(item, dict):
        return None
    choices = item.get("choices")
    answer = item.get("answer")
    if (not isinstance(item.get("q"), str) or not item["q"].strip()
            or not isinstance(choices, list) or len(choices) != 4
            or not all(isinstance(c, str) for c in choices)
            or not isinstance(answer, int) or not 0 <= answer <= 3):
        return None
    return {
        "q": item["q"].strip(),
        "choices": [c.strip() for c in choices],
        "answer": answer,
        "explanation": str(item.get("explanation", "")).strip(),
    }


def fetch_questions(theme, num):
    """N問を取得する。1回リトライ＋使える問だけ救済。戻り: (questions, theme_name)。"""
    theme_line = "テーマはおまかせで" if not theme else "テーマは「{}」で".format(theme)
    prompt = (
        "クイズを{}{}問作ってください。4択で、難易度に波をつけてください。"
        "回答はJSONのみを出力してください。説明文や前置きは不要です。"
        "形式: {{\"theme\": \"テーマ名\", \"questions\": ["
        "{{\"q\": \"問題文\", \"choices\": [\"選択肢1\", \"選択肢2\", "
        "\"選択肢3\", \"選択肢4\"], \"answer\": 0, "
        "\"explanation\": \"解説文\"}}]}}"
        "answerは正解の番号（0-3）です。"
    ).format(theme_line, num)
    last_err = ""
    for _ in (1, 2):
        ok, text = ask_gemini(prompt)
        if not ok:
            last_err = text
            continue
        try:
            data = extract_json(text)
            raw = data.get("questions", []) if isinstance(data, dict) else []
        except ValueError as exc:
            last_err = "JSON解析に失敗: {}".format(exc)
            continue
        questions = [q for q in (valid_question(i) for i in raw) if q]
        if questions:
            theme_name = data.get("theme", "") if isinstance(data, dict) else ""
            return questions[:num], str(theme_name or "おまかせ")
        last_err = "有効な問題が0問"
    return [], last_err


def read_line(prompt):
    """1行入力。EOF時はNoneを返す（呼び出し側で中止扱いにする）。"""
    try:
        return input(prompt).strip()
    except EOFError:
        return None


def comment_for(score, total):
    """結果寸評。"""
    if total <= 0:
        return "問題なし"
    rate = score / total
    if rate >= 0.8:
        return "見事。全問級の冴え"
    if rate >= 0.5:
        return "まずまず。もう一押し"
    return "伸びしろ十分。復習で取り返そう"


def main():
    safe_console()
    parser = argparse.ArgumentParser(description="Geminiおまかせクイズゲーム")
    parser.add_argument("--num", type=int, default=DEFAULT_NUM)
    args = parser.parse_args()
    num = min(max(args.num, 1), 10)

    quota = ask_quota()
    five = quota.get("gemini_5h")
    if five is not None and five <= QUOTA_STOP_THRESHOLD:
        print("残量{}%のため開始しません（7%以下は停止）。またの機会に。".format(five))
        return 2
    if five is not None:
        print("残量{}%。遊びましょう。".format(five))

    theme_raw = read_line("テーマをどうぞ（空Enterでおまかせ）: ")
    if theme_raw is None:
        print("\n中止しました。")
        return 130
    theme = theme_raw
    print("出題を生成中…")
    questions, meta = fetch_questions(theme, num)
    if not questions:
        print("出題の生成に失敗: {}".format(meta))
        return 1
    print("テーマ: {}".format(meta))

    score = 0
    for i, item in enumerate(questions, 1):
        print("\nQ{}: {}".format(i, item["q"]))
        for n, choice in enumerate(item["choices"], 1):
            print("  {}. {}".format(n, choice))
        while True:
            raw = read_line("回答 (1-4): ")
            if raw is None:
                print("\n中止しました。")
                return 130
            if raw in ("1", "2", "3", "4"):
                picked = int(raw) - 1
                break
            print("1-4で入力してください。")
        if picked == item["answer"]:
            print("正解")
            score += 1
        else:
            print("不正解。正解は {} です。".format(item["answer"] + 1))
        if item["explanation"]:
            print("解説: {}".format(item["explanation"]))

    total = len(questions)
    print("\n結果: {}/{}。{}".format(score, total, comment_for(score, total)))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n中止しました。")
        sys.exit(130)
