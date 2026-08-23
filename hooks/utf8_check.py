"""pre-commit: UTF-8破損チェック + フッタ検証（警告） + coreファイルセクション存在チェック"""
import sys, subprocess, os, re

def put(s):
    sys.stdout.buffer.write(s.encode('utf-8'))
    sys.stdout.buffer.write(b'\n')
    sys.stdout.buffer.flush()

CORE_FILES = [".opencore/rules/phronisis.md", "knowledge/handover.md", "AGENTS.md"]
PHRO_MANDATORY = ["最上位原則", "構成", "判断の三層構造"]

def get_staged_files():
    r = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"], capture_output=True, text=True)
    return [f for f in r.stdout.splitlines() if f.endswith(".md")]

def check_utf8(path):
    try:
        with open(path, "rb") as f:
            f.read().decode("utf-8")
        return None
    except UnicodeDecodeError as e:
        return f"{path}: UTF-8破損 ({e})"

def check_footer(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    # 末尾固定+agent名必須検証（部分一致だと本文中の言及を誤検出するため）
    import re
    # completeフッタの完全形式（agent必須）
    full = re.search(r"<!-- status: complete\s*\|\s*agent:\s*\S+\s*-->\s*$", content)
    # agentなしcomplete（移行漏れの検出。WARN対象）
    no_agent = re.search(r"<!-- status: complete\s*-->\s*$", content)
    if no_agent and not full:
        return f"{path}: フッタがagentなし（<!-- status: complete -->）。agent必須（<!-- status: complete | agent: NAME -->）に修正"
    if not full and not no_agent:
        return f"{path}: フッタ（<!-- status: complete | agent: NAME --> を末尾に）なし"
    return None

def check_core_sections(path):
    """phronisis.md の必須セクション存在チェック"""
    if not path.endswith("phronisis.md"):
        return None
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    missing = [s for s in PHRO_MANDATORY if s not in content]
    if missing:
        return f"{path}: 必須セクションがありません: {missing}"
    return None

def check_commit_message():
    """コミットメッセージ形式を検証（YYMMDD_英名 or それ以外も許容、警告のみ）"""
    msg_path = subprocess.run(["git", "rev-parse", "--git-dir"], capture_output=True, text=True)
    if msg_path.returncode != 0:
        return None
    msg_file = os.path.join(msg_path.stdout.strip(), "COMMIT_EDITMSG")
    if not os.path.exists(msg_file):
        return None
    with open(msg_file, "r", encoding="utf-8") as f:
        first_line = f.readline().strip()
    if not first_line:
        return None
    # 初期コミットやマージコミットはスキップ
    if first_line.startswith("Initial commit") or first_line.startswith("Merge"):
        return None
    if re.match(r"^\d{6}_[a-z]", first_line):
        return None  # 命名規則準拠
    # chore/fix/feat 等のプレフィックスは許容
    if re.match(r"^(chore|fix|feat|docs|refactor|test|style|WIP|wip)", first_line, re.IGNORECASE):
        return None
    return f"コミットメッセージが命名規則（YYMMDD_英名, chore:〜, fix:〜 等）に沿っていません: {first_line[:60]}"

def show_core_diff():
    """coreファイルが変更されていたら差分行数を表示"""
    r = subprocess.run(["git", "diff", "--cached", "--stat", "--"] + CORE_FILES, capture_output=True, text=True)
    if r.stdout.strip():
        put("\n--- coreファイル変更検出 ---")
        put(r.stdout.strip())
        put("---------------------------\n")

problems = []
has_core = False
for f in get_staged_files():
    if not os.path.exists(f):
        continue
    if f in CORE_FILES:
        has_core = True
    err = check_utf8(f)
    if err:
        problems.append(("BLOCK", err))
        continue
    warn = check_footer(f)
    if warn:
        problems.append(("WARN", warn))
    sec = check_core_sections(f)
    if sec:
        problems.append(("WARN", sec))

if has_core:
    show_core_diff()

# コミットメッセージチェック
commit_warn = check_commit_message()
if commit_warn:
    problems.append(("WARN", commit_warn))

for severity, msg in problems:
    if severity == "BLOCK":
        put(f"[BLOCK] {msg}")
    else:
        put(f"[WARN] {msg}")

if any(s == "BLOCK" for s, _ in problems):
    put("ブロック対象のエラーを検出しました。修正して再ステージしてください。")
    sys.exit(1)
sys.exit(0)
