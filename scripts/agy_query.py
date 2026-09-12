#!/usr/bin/env python3
"""
agy_query.py — Antigravity CLI (agy) 外部AIブリッジ（PhronisisCode適応版）

Code適応注記:
- 出典: 本家 PhronisisCore commit db1a221 の reference/agy_query.py を最小差分で適応。
- REPO_ROOTはCodeのscripts直下配置でも親がリポジトリ直下で成立。外部パス拒否はCode側に自動切替。
- Code運用は ask / quota（+generate手順のみ）に限定。extract不使用。API自動フォールバックなし（agy-only。黙って課金落ちしない）。
- コード上のextract/--auto-model/API分岐は本家追従のため温存。Code運用では呼ばない。
- 詳細は knowledge/code_knowledge/agy.md、由来は shared/phronisis_code/protocol/evolution_log.md を参照。

Google公式の Antigravity CLI (`agy`) を、Googleアカウントのサブスク認証で呼び出す。
APIキーは不要。従量課金の外で Gemini / Claude / GPT-OSS を下処理に使うためのブリッジ。

用途:
  extract  画像 / PDF からテキスト・構造を抽出（OCR・資料解析）(Code不使用・温存)
  ask      任意プロンプトを投げて回答を得る（外部知能の意見）
  generate プロンプトから画像を生成し、指定先へ保存
  quota    サブスクの残量（Gemini / Claude+GPT の5時間・週次）を取得

設計原則:
  - フロニシス外に一時ワークスペースを作らない。対象ファイルの親ディレクトリを cwd にし、
    リポジトリ内で完結させる（外部パス権限プロンプトを避ける設計。ユーザー観測レベルの確認は未実施）。
    リポジトリ外のファイルは extract が拒否する。
  - agy は `--dangerously-skip-permissions` を付けてヘッドレス実行する。書き込み事故を防ぐため、
    プロンプトで「ファイルを変更するな」を明示し、抽出は読み取り専用で運用する。
  - 出力はバイト取得→UTF-8デコード（Windowsコンソール(cp932)経由の文字化けを回避）。
  - agy はエージェントのため、曖昧・相対パス指示だと narration だけ返すことがある。
    絶対パスを強制し、narration検出時は1回リトライする。

注意:
  - agy は自前の `~/.gemini/antigravity-cli/scratch/` に画像を保存する。
    生成物はラッパー側でコピーして取り込む（Kaiが外部パスを直接操作しない）。
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_MODEL_HIGH = "Gemini 3.8 Flash (High)"
DEFAULT_MODEL_MEDIUM = "Gemini 3.8 Flash (Medium)"
# モデル名に effort(High/Medium/Low) が内包されているため、既定では --effort を渡さない。
# ベースモデル（サフィックス無し）を使う場合のみ明示指定する。
DEFAULT_EFFORT = None
DEFAULT_TIMEOUT = 180

# クォータ閾値（5時間残 %）
QUOTA_HIGH_THRESHOLD = 30   # これ超: High
QUOTA_API_THRESHOLD = 7     # これ以下: APIフォールバック要求

# get_quota のバッチ向けキャッシュ（agyパス, 残量, 取得時刻）
_QUOTA_CACHE = {"agy": None, "value": None, "ts": 0.0}

EXTRACT_PREAMBLE = (
    "You are a document extraction tool. Read ONLY the file at the absolute path below.\n"
    "Absolute path: {path}\n"
    "Do not search other directories. Do not create, modify, rename, or delete any files.\n"
    "Do not output progress, status updates, or meta commentary. Do not narrate tool use.\n"
    "Output ONLY the requested content immediately.\n\n"
)

EXTRACT_INSTRUCTIONS = {
    "screenshot": (
        "この画像はスクリーンショットまたはWebキャプチャです。"
        "表示されているテキストを全て抽出し、見出し・リスト・段落の階層構造を保持したMarkdown形式で出力してください。"
        "コードブロック、テーブル、UI要素があれば正確に再現してください。"
        "最後に確信度(0-10)と不明瞭な箇所があれば記載してください。"
    ),
    "scan": (
        "この画像はスキャン文書または資料写真です。"
        "テキストを正確に転記し、セクション見出し・箇条書き・注釈を保持してください。"
        "手書き部分は特に注意深く抽出し、判読不能な箇所は明示してください。"
        "最後に確信度(0-10)と不明瞭な箇所があれば記載してください。"
    ),
    "whiteboard": (
        "この画像はホワイトボードまたはフローチャートの写真です。"
        "図の構造（要素間の関係・矢印・階層）を説明し、テキスト要素を全て抽出してください。"
        "可能であればMermaid形式での再現を試みてください。"
        "最後に確信度(0-10)と不明瞭な箇所があれば記載してください。"
    ),
    "pdf": (
        "このPDFは企画書・報告書・資料です。"
        "全ページの内容を構造化テキストで抽出してください。"
        "セクション見出し・箇条書き・表・図表の説明を保持したMarkdown形式で出力してください。"
        "ページ番号を明記し、ページ間の文脈の連続性を維持してください。"
        "最後に確信度(0-10)と不明瞭な箇所があれば記載してください。"
    ),
}

DEFAULT_INSTRUCTION = (
    "この内容を構造化テキストで説明してください。"
    "テキスト要素・レイアウト・図表を正確に抽出し、Markdown形式で出力してください。"
    "最後に確信度(0-10)と不明瞭な箇所があれば記載してください。"
)

# narration（進捗・状況説明だけで終わった応答）の検出マーカー
NARRATION_MARKERS = (
    "お待ちください",
    "確認しています",
    "検索しています",
    "実行しています",
    "調べています",
    "処理しています",
    "少々お待ち",
)

# cp932誤デコード（UTF-8バイトをcp932で読んだ痕跡）に現れやすい文字。
# 単体では正当な漢字（隕石・縺れる・喧譁等）になりうるため、単独出現では判定しない。
MOJIBAKE_CHARS = "縺繧繝譁隕"
MOJIBAKE_RUN_THRESHOLD = 3


def looks_garbled(text):
    """文字化けの疑いを検出する安全弁。
    U+FFFD（不正バイト）または cp932誤デコード痕跡文字の多発(>=3)で判定する。
    ヒューリスティックであり、単発の正規漢字を誤検知しないことを優先する。
    限界: Latin-1系の化け（Ã©等）や痕跡文字が2個以下の化けはすり抜けうる。"""
    if not text:
        return False
    if "\ufffd" in text:
        return True
    return sum(text.count(c) for c in MOJIBAKE_CHARS) >= MOJIBAKE_RUN_THRESHOLD


def write_utf8(text):
    """UTF-8でstdoutへ書く（cp932経由の文字化け回避）。"""
    data = text.encode("utf-8", errors="replace")
    sys.stdout.buffer.write(data)
    if not data.endswith(b"\n"):
        sys.stdout.buffer.write(b"\n")
    sys.stdout.buffer.flush()


def write_utf8_stderr(text):
    """UTF-8でstderrへ書く（非ASCIIの二次エンコード例外を避ける）。"""
    sys.stderr.buffer.write(text.encode("utf-8", errors="replace"))
    sys.stderr.buffer.write(b"\n")
    sys.stderr.buffer.flush()


def find_agy():
    """agy バイナリを解決する。
    既定のCLIインストール先をPATHより優先する（MacでAntigravity IDEの `agy` ラッパー等、
    PATH上の別物を掴まないため）。既定パスに無ければPATHにフォールバック。"""
    candidates = []
    localappdata = os.environ.get("LOCALAPPDATA")
    if localappdata:
        candidates.append(Path(localappdata) / "agy" / "bin" / "agy.exe")
        candidates.append(Path(localappdata) / "agy" / "bin" / "agy")
    candidates.append(Path.home() / ".local" / "bin" / "agy")
    for c in candidates:
        if c.exists():
            return str(c)
    return shutil.which("agy")


def agy_scratch_dir():
    return Path.home() / ".gemini" / "antigravity-cli" / "scratch"


def _decode(data):
    return data.decode("utf-8", errors="replace") if data else ""


def run_agy(agy, prompt, cwd, model=None, effort=None, timeout=DEFAULT_TIMEOUT,
            conversation=None, continue_=False, output_format="json"):
    """agy をヘッドレス実行し、(returncode, stdout, stderr) を返す。"""
    cmd = [agy, "-p", prompt,
           "--print-timeout", f"{timeout}s",
           "--dangerously-skip-permissions",
           "--output-format", output_format]
    if model:
        cmd += ["--model", model]
    if effort:
        cmd += ["--effort", effort]
    if conversation:
        cmd += ["--conversation", str(conversation)]
    elif continue_:
        cmd += ["--continue"]
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True)
    return proc.returncode, _decode(proc.stdout), _decode(proc.stderr)


def parse_response(stdout):
    """JSON出力から response と会話メタを取り出す。"""
    text = (stdout or "").strip()
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return text, {}
    return data.get("response", ""), data


def looks_like_narration(text):
    t = (text or "").strip()
    if not t:
        return True
    if len(t) > 160:
        return False
    return any(m in t for m in NARRATION_MARKERS)


# ---------------------------------------------------------------------------
# quota
# ---------------------------------------------------------------------------

def _parse_usage_text(text):
    q = {}
    mapping = {
        ("Gemini Models", "Weekly"): "gemini_weekly",
        ("Gemini Models", "Five Hour"): "gemini_5h",
        ("Claude and GPT models", "Weekly"): "cgpt_weekly",
        ("Claude and GPT models", "Five Hour"): "cgpt_5h",
    }
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or "%" not in line:
            continue
        parts = [p.strip() for p in line.split("\t")] if "\t" in line else line.split()
        pct = None
        for p in parts:
            if p.endswith("%"):
                try:
                    pct = int(p.rstrip("%").strip())
                except ValueError:
                    pct = None
                break
        if pct is None:
            continue
        joined = " ".join(parts).lower()
        for (group, kind), key in mapping.items():
            if group.lower() in joined and kind.lower() in joined:
                q[key] = pct
                break
    return q


def get_quota(agy, timeout=90, ttl=300):
    """`agy -p /usage` を叩いて残量(%)を辞書で返す。取得不能項目は含めない。
    バッチ処理で毎回agyを起動しないよう、ttl秒間キャッシュする。"""
    now = time.time()
    if _QUOTA_CACHE["agy"] == agy and _QUOTA_CACHE["value"] is not None:
        cached = _QUOTA_CACHE["value"]
        age = now - _QUOTA_CACHE["ts"]
        # 取得成功: ttl秒キャッシュ / 取得失敗(空): 60秒だけネガティブキャッシュ
        if age < (ttl if cached else 60):
            return cached
    rc, stdout, stderr = run_agy(agy, "/usage", REPO_ROOT, timeout=timeout, output_format="text")
    q = _parse_usage_text(stdout)
    if not q:
        q = _parse_usage_text(stderr)
    _QUOTA_CACHE.update({"agy": agy, "value": q, "ts": now})
    return q


def select_model(quota, high_threshold=QUOTA_HIGH_THRESHOLD, api_threshold=QUOTA_API_THRESHOLD):
    """5時間残に応じてモデル階層を選ぶ。'API' は APIフォールバック要求を意味する。"""
    five = quota.get("gemini_5h")
    if five is None:
        return DEFAULT_MODEL_HIGH
    if five <= api_threshold:
        return "API"
    if five <= high_threshold:
        return DEFAULT_MODEL_MEDIUM
    return DEFAULT_MODEL_HIGH


def model_for_generation(agy, quota=None, high_threshold=QUOTA_HIGH_THRESHOLD,
                         api_threshold=QUOTA_API_THRESHOLD):
    """画像生成用モデルを選ぶ。API代替が無いため、閾値以下ではHighではなくMediumに落とす。
    戻り: (model, quota_low)。quota未指定なら取得する。"""
    if quota is None:
        quota = get_quota(agy)
    selection = select_model(quota, high_threshold, api_threshold)
    quota_low = selection == "API"
    return (DEFAULT_MODEL_MEDIUM if quota_low else selection), quota_low


# ---------------------------------------------------------------------------
# extract / ask
# ---------------------------------------------------------------------------

def extract(agy, file_path, type_=None, instruction=None, model=None,
            effort=DEFAULT_EFFORT, timeout=DEFAULT_TIMEOUT):
    """画像/PDFからテキストを抽出する。戻り: (ok, text, meta)"""
    src = Path(file_path).resolve()
    if not src.exists():
        return False, "", {"error": f"file not found: {src}"}
    try:
        src.relative_to(REPO_ROOT)
    except ValueError:
        return False, "", {
            "engine": "agy",
            "error": f"file is outside repository (refused to avoid external-path prompt): {src}",
        }
    if type_:
        instr = EXTRACT_INSTRUCTIONS.get(type_, DEFAULT_INSTRUCTION)
    else:
        instr = instruction or DEFAULT_INSTRUCTION
    prompt = EXTRACT_PREAMBLE.format(path=str(src)) + instr

    last_err = ""
    for attempt in (1, 2):
        rc, stdout, stderr = run_agy(
            agy, prompt, src.parent, model=model, effort=effort, timeout=timeout)
        text, data = parse_response(stdout)
        if rc == 0 and text and not looks_like_narration(text) and not looks_garbled(text):
            return True, text, {
                "engine": "agy",
                "model": model,
                "conversation_id": data.get("conversation_id"),
                "usage": data.get("usage"),
                "attempts": attempt,
            }
        if looks_garbled(text):
            last_err = "garbled output detected (UTF-8 integrity check failed)"
        else:
            last_err = (stderr or stdout or "").strip()[:500]
    return False, "", {"engine": "agy", "error": last_err or "no output"}


def ask(agy, prompt, model=None, effort=DEFAULT_EFFORT, timeout=DEFAULT_TIMEOUT,
        cwd=None, conversation=None):
    """任意プロンプトの回答を得る。戻り: (ok, text, meta)"""
    rc, stdout, stderr = run_agy(
        agy, prompt, cwd or REPO_ROOT, model=model, effort=effort,
        timeout=timeout, conversation=conversation)
    text, data = parse_response(stdout)
    ok = rc == 0 and bool(text.strip()) and not looks_garbled(text)
    meta = {"engine": "agy", "model": model,
            "conversation_id": data.get("conversation_id"),
            "usage": data.get("usage")}
    if not ok:
        if looks_garbled(text):
            meta["error"] = "garbled output detected (UTF-8 integrity check failed)"
        else:
            meta["error"] = (stderr or stdout or "").strip()[:500]
    return ok, text, meta


# ---------------------------------------------------------------------------
# generate
# ---------------------------------------------------------------------------

def _snapshot(directory):
    snap = {}
    if directory.exists():
        for p in directory.iterdir():
            if p.is_file():
                try:
                    snap[p.name] = p.stat().st_mtime
                except OSError:
                    pass
    return snap


def generate(agy, prompt, out_path, model=None, effort=DEFAULT_EFFORT,
             timeout=DEFAULT_TIMEOUT, conversation=None):
    """画像を生成（または会話を引き継いで修正）し、out_path に保存する。
    戻り: (ok, meta)"""
    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    scratch = agy_scratch_dir()
    scratch.mkdir(parents=True, exist_ok=True)
    target_name = out_path.name
    before = _snapshot(scratch)

    if conversation:
        head = "Modify the previously generated image according to this instruction: "
    else:
        head = "Generate an image according to this instruction: "
    gen_prompt = (
        f"{head}{prompt}\n"
        f"Save the resulting image with the exact filename '{target_name}' in your scratch directory. "
        f"The absolute path must be {scratch / target_name}. "
        "Do not modify any other files. Output only a one-line confirmation containing the saved path."
    )

    rc, stdout, stderr = run_agy(
        agy, gen_prompt, REPO_ROOT, model=model, effort=effort,
        timeout=timeout, conversation=conversation)
    text, data = parse_response(stdout)

    # 生成物を特定: 同名優先、無ければ新規/更新された最新ファイル
    chosen = None
    exact = scratch / target_name
    if exact.exists() and (exact.name not in before or exact.stat().st_mtime > before.get(exact.name, 0)):
        chosen = exact
    if chosen is None:
        candidates = []
        for p in scratch.iterdir():
            if not p.is_file():
                continue
            mtime = p.stat().st_mtime
            if p.name not in before or mtime > before.get(p.name, 0):
                candidates.append((mtime, p))
        if candidates:
            chosen = max(candidates, key=lambda x: x[0])[1]

    if chosen is None:
        return False, {"engine": "agy", "model": model,
                       "error": (stderr or stdout or "").strip()[:500] or "no image produced"}

    shutil.copy2(chosen, out_path)
    return True, {
        "engine": "agy",
        "model": model,
        "output": str(out_path),
        "conversation_id": data.get("conversation_id"),
        "reply": text.strip()[:300],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _require_agy():
    agy = find_agy()
    if not agy:
        write_utf8("ERROR: agy binary not found. Install Antigravity CLI first.")
        sys.exit(2)
    return agy


def _emit_json(obj):
    write_utf8(json.dumps(obj, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Antigravity CLI (agy) 外部AIブリッジ")
    sub = parser.add_subparsers(dest="command")

    p_ext = sub.add_parser("extract", help="画像/PDFからテキスト抽出")
    p_ext.add_argument("--file", required=True)
    p_ext.add_argument("--type", choices=list(EXTRACT_INSTRUCTIONS.keys()), default=None)
    p_ext.add_argument("--instruction", default=None)
    p_ext.add_argument("--model", default=DEFAULT_MODEL_HIGH)
    p_ext.add_argument("--effort", default=DEFAULT_EFFORT,
                       choices=["low", "medium", "high"])
    p_ext.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    p_ext.add_argument("--auto-model", action="store_true",
                       help="クォータに応じてモデル階層を自動選択")

    p_ask = sub.add_parser("ask", help="任意プロンプトの回答を得る")
    p_ask.add_argument("prompt")
    p_ask.add_argument("--model", default=DEFAULT_MODEL_HIGH)
    p_ask.add_argument("--effort", default=DEFAULT_EFFORT,
                       choices=["low", "medium", "high"])
    p_ask.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)

    p_gen = sub.add_parser("generate", help="画像生成 / 修正")
    p_gen.add_argument("prompt")
    p_gen.add_argument("--out", required=True)
    p_gen.add_argument("--conversation", default=None)
    p_gen.add_argument("--model", default=None,
                       help="未指定ならクォータに応じて自動選択（7%以下はMedium）")
    p_gen.add_argument("--effort", default=DEFAULT_EFFORT,
                       choices=["low", "medium", "high"])
    p_gen.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)

    sub.add_parser("quota", help="サブスク残量を取得")

    args = parser.parse_args()

    if args.command == "quota":
        agy = _require_agy()
        _emit_json(get_quota(agy))
        return

    if args.command == "extract":
        agy = _require_agy()
        model = args.model
        if args.auto_model:
            selection = select_model(get_quota(agy))
            if selection == "API":
                write_utf8_stderr(json.dumps(
                    {"engine": "agy", "error": "quota below threshold; caller should use API fallback"},
                    ensure_ascii=False))
                sys.exit(3)
            model = selection
        ok, text, meta = extract(agy, args.file, type_=args.type,
                                 instruction=args.instruction, model=model,
                                 effort=args.effort, timeout=args.timeout)
        if ok:
            write_utf8(text)
        else:
            write_utf8_stderr(json.dumps(meta, ensure_ascii=False))
            sys.exit(1)
        return

    if args.command == "ask":
        agy = _require_agy()
        ok, text, meta = ask(agy, args.prompt, model=args.model,
                             effort=args.effort, timeout=args.timeout)
        if ok:
            write_utf8(text)
        else:
            write_utf8_stderr(json.dumps(meta, ensure_ascii=False))
            sys.exit(1)
        return

    if args.command == "generate":
        agy = _require_agy()
        if args.model:
            model, quota_low = args.model, None
        else:
            model, quota_low = model_for_generation(agy)
        ok, meta = generate(agy, args.prompt, args.out, model=model,
                            effort=args.effort, timeout=args.timeout,
                            conversation=args.conversation)
        meta["quota_low"] = quota_low
        _emit_json({"success": ok, **meta})
        if not ok:
            sys.exit(1)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
