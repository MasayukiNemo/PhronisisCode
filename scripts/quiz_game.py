#!/usr/bin/env python3
"""
quiz_game.py — Geminiおまかせクイズゲーム（CLI対話式）

agy経由Geminiにテーマ・出題・解説を任せる4択クイズ。標準ライブラリのみ。
conduct準拠: ask前にquota確認、7%以下は停止。
PyInstaller onefile化対応: agy呼出はimport取込（frozen時にscripts相対が崩れない）。

遊び方:
    python scripts/quiz_game.py [--num 5] [--difficulty 2]
    dist/quiz_game.exe
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import agy_query
except ImportError:
    agy_query = None

QUOTA_STOP_THRESHOLD = 7
DEFAULT_NUM = 5
DEFAULT_DIFFICULTY = 2

DIFFICULTY = {
    1: ("おてがる", "小学生にもわかるやさしい言葉で、基本的な内容を"),
    2: ("ふつう", "一般的な知識レベルで、素直な内容を"),
    3: ("チャレンジ", "ひねりや応用を効かせて、考えさせる内容を"),
    4: ("マニア", "専門家も唸る細部・専門知識を突いた内容を"),
}

# 難易度別の字数目安（問題/選択肢/解説）。マニアは内容優先で緩める
LENGTH = {
    1: (150, 40, 200),
    2: (200, 60, 300),
    3: (300, 80, 400),
    4: (300, 70, 400),
}


def safe_console():
    """cp932コンソールで落ちないよう置換出力にする（表示崩れと実害を分離）。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def base_dir():
    """agyのcwd用。frozen時はexe所在、通常時はリポジトリ直下。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def require_agy():
    """agyバイナリを解決する。無ければ例外メッセージを返す。"""
    if agy_query is None:
        return None, "agy_queryモジュールが見つかりません"
    agy = agy_query.find_agy()
    if not agy:
        return None, "agy binary not found. Install Antigravity CLI first."
    return agy, ""


def ask_quota(agy):
    """残量JSONを返す。取得不能時は空辞書。"""
    try:
        data = agy_query.get_quota(agy)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def ask_gemini(agy, prompt, cwd, timeout=180):
    """agy askを1回投げる。戻り: (ok, text)。"""
    try:
        ok, text, meta = agy_query.ask(
            agy, prompt, timeout=timeout, cwd=str(cwd))
    except Exception as exc:
        return False, "ask実行に失敗: {}".format(exc)
    if not ok:
        return False, str((meta or {}).get("error", "") or "応答なし")[:300]
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
            or not all(isinstance(c, str) and c.strip() for c in choices)
            or not isinstance(answer, int) or not 0 <= answer <= 3):
        return None
    return {
        "q": item["q"].strip(),
        "choices": [c.strip() for c in choices],
        "answer": answer,
        "explanation": str(item.get("explanation", "")).strip(),
    }


def fetch_questions(agy, cwd, theme, num, difficulty, verbose=False,
                    on_retry=None):
    """N問まとめ取り（1ask）。1回リトライ＋使える問だけ救済。
    戻り: (questions, meta文)。quota節約のため逐次化しない。"""
    name, desc = DIFFICULTY[difficulty]
    qlen, clen, elen = LENGTH[difficulty]
    theme_line = "テーマはおまかせで" if not theme else "テーマは「{}」で".format(theme)
    prompt = (
        "クイズを{}{}問作ってください。難易度「{}」として、{}"
        "難易度に波をつけすぎず、このレベルで揃えてください。"
        "回答はJSONのみを出力してください。説明文や前置きは不要です。"
        "情報が少ないテーマでも言い訳・謝罪・前置きを書かず、作れる範囲でJSONのみを出力してください。"
        "形式: {{\"theme\": \"テーマ名\", \"questions\": ["
        "{{\"q\": \"問題文\", \"choices\": [\"選択肢1\", \"選択肢2\", "
        "\"選択肢3\", \"選択肢4\"], \"answer\": 0, "
        "\"explanation\": \"解説文\"}}]}}"
        "answerは正解の番号（0-3）です。正解番号は各問でばらけさせてください。"
        "偽の選択肢は、同カテゴリ・同形式で長さを揃え、ありがちな誤解や隣接概念を使ってください。"
        "「すべて正しい」「すべて誤り」「上記のすべて」系の選択肢は禁止です。"
        "問題文は{}字以内、選択肢は各{}字以内、解説は{}字以内を目安にしてください。"
        "ただし内容の正確さと専門性を字数より優先してください。"
    ).format(theme_line, num, name, desc, qlen, clen, elen)
    last_err = ""
    timeout = 90 + 60 * num
    for attempt in (1, 2):
        if attempt == 2:
            if verbose:
                print("（再試行中）")
            if on_retry:
                on_retry()
        ok, text = ask_gemini(agy, prompt, cwd, timeout=timeout)
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
            note = ""
            if len(questions) < num:
                note = "（{}問分のみ取得）".format(len(questions))
            return questions[:num], "{}{}".format(theme_name or "おまかせ", note)
        last_err = "有効な問題が0問"
    return [], last_err


def read_line(prompt):
    """1行入力。EOF時はNoneを返す（呼び出し側で中止扱いにする）。"""
    try:
        return input(prompt).strip()
    except EOFError:
        return None


def ask_choice(prompt, lo, hi, default):
    """数値選択。空Enterでデフォルト、範囲外・非数値は再入力、EOFはNone。"""
    while True:
        raw = read_line("{} ({}-{}、空={}): ".format(prompt, lo, hi, default))
        if raw is None:
            return None
        if raw == "":
            return default
        try:
            value = int(raw)
        except ValueError:
            print("{}-{}で入力してください。".format(lo, hi))
            continue
        if lo <= value <= hi:
            return value
        print("{}-{}で入力してください。".format(lo, hi))


def comment_for(score, total, theme="", diff=""):
    """結果寸評。tier別に複数文型から選ぶ（固定文の使い回しにしない）。"""
    import random
    topic = "「{}」".format(theme) if theme else "今回"
    level = "（難易度:{}）".format(diff) if diff else ""
    if total <= 0:
        return "問題なし"
    rate = score / total
    if rate >= 0.8:
        pool = [
            "{s}/{t}。{topic}はほぼ制圧{lv}、見事な冴え",
            "{s}/{t}{lv}。{topic}の急所を外さない、いい腕だ",
            "{s}/{t}。{topic}に関しては人に教えられる側だな",
        ]
    elif rate >= 0.5:
        pool = [
            "{s}/{t}{lv}。{topic}は半分制圧、もう一押しだ",
            "{s}/{t}。{topic}の勘所は掴んでいる、あと一息だな",
            "{s}/{t}{lv}。惜しい取りこぼしがある、復習で埋めよう",
        ]
    else:
        pool = [
            "{s}/{t}{lv}。{topic}は伸びしろ十分、解説を武器に取り返そう",
            "{s}/{t}。{topic}の土台作りからだな、次が楽しみだ",
            "{s}/{t}{lv}。今日の種を拾えただけでも収穫だ、次に繋げよう",
        ]
    return random.choice(pool).format(
        s=score, t=total, topic=topic, lv=level)


def main():
    safe_console()
    parser = argparse.ArgumentParser(description="Geminiおまかせクイズゲーム")
    parser.add_argument("--num", type=int, default=None)
    parser.add_argument("--difficulty", type=int, default=None,
                        choices=list(DIFFICULTY))
    args = parser.parse_args()

    agy, agy_err = require_agy()
    if agy is None:
        print("開始できません: {}".format(agy_err))
        return 2
    cwd = base_dir()

    quota = ask_quota(agy)
    five = quota.get("gemini_5h")
    if five is not None and five <= QUOTA_STOP_THRESHOLD:
        print("残量{}%のため開始しません（7%以下は停止）。またの機会に。".format(five))
        return 2
    if five is not None:
        print("残量{}%。遊びましょう。".format(five))
    else:
        print("残量を取得できませんでした。続行します。")

    theme_raw = read_line("テーマをどうぞ（空Enterでおまかせ）: ")
    if theme_raw is None:
        print("\n中止しました。")
        return 130
    if args.num is not None:
        if not 1 <= args.num <= 10:
            print("--numは1-10で指定してください（{}は範囲外のため5問にします）。".format(args.num))
        num = min(max(args.num, 1), 10)
    else:
        num = ask_choice("設問数", 1, 10, DEFAULT_NUM)
        if num is None:
            print("\n中止しました。")
            return 130
    if args.difficulty is not None:
        difficulty = args.difficulty
    else:
        print("難易度: " + " / ".join(
            "{}={}".format(k, v[0]) for k, v in sorted(DIFFICULTY.items())))
        difficulty = ask_choice("難易度", 1, 4, DEFAULT_DIFFICULTY)
        if difficulty is None:
            print("\n中止しました。")
            return 130

    print("出題を生成中…")
    started = time.time()
    questions, meta = fetch_questions(
        agy, cwd, theme_raw, num, difficulty, verbose=True)
    print("（生成に{}秒かかりました）".format(int(time.time() - started)))
    if not questions:
        print("出題の生成に失敗: {}".format(meta))
        return 1
    print("テーマ: {} / 難易度: {}".format(meta, DIFFICULTY[difficulty][0]))

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
    print("\n結果: {}".format(
        comment_for(score, total, meta, DIFFICULTY[difficulty][0])))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n中止しました。")
        sys.exit(130)
