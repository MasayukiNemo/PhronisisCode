"""pre-push: handover陳腐化検出 + session_log整合性 + coreファイル差分"""
import sys, subprocess, os, re

CORE_FILES = [".opencore/rules/phronisis_code.md", "knowledge/handover.md", "AGENTS.md"]

def get_head_blob(path):
    """HEAD 時点のファイル blob SHA"""
    r = subprocess.run(["git", "rev-parse", f"HEAD:{path}"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None

# 最適化（2026-08-15）: git ls-remote はネットワーク通信（約1.5秒/回）。
# リモートHEADのSHAを1回だけ取得して handover.md の陳腐化チェックに使う。
# 取得に失敗した場合も確定値として記録し、再取得しない（失敗時も1回保証）。
_remote_head_sha = "NOT_FETCHED"
def get_remote_head_sha():
    """リモートHEADのSHAを1回だけ取得して使い回す（失敗も含めて確定）"""
    global _remote_head_sha
    if _remote_head_sha == "NOT_FETCHED":
        r = subprocess.run(["git", "ls-remote", "origin", "HEAD"], capture_output=True, text=True)
        _remote_head_sha = r.stdout.split()[0] if (r.returncode == 0 and r.stdout.strip()) else None
    return _remote_head_sha

def get_remote_head_blob(path):
    """リモートHEAD時点のファイル blob SHA（ls-remoteは1回のみ）"""
    r_head = get_remote_head_sha()
    if r_head is None:
        return None
    r2 = subprocess.run(["git", "ls-tree", r_head, path], capture_output=True, text=True)
    return r2.stdout.split()[2].split()[0] if r2.stdout.strip() else None

def get_merge_base_blob(remote, path):
    """merge base 時点のファイル blob SHA"""
    r = subprocess.run(["git", "merge-base", "HEAD", f"{remote}/main"], capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        return None
    mb = r.stdout.strip()
    r2 = subprocess.run(["git", "ls-tree", mb, path], capture_output=True, text=True)
    return r2.stdout.split()[2].split()[0] if r2.stdout.strip() else None

# handover.md 陳腐化チェック
ho_remote = get_remote_head_blob("knowledge/handover.md")
ho_head = get_head_blob("knowledge/handover.md")
ho_base = get_merge_base_blob("origin", "knowledge/handover.md")

# フェイルオープン対策: リモート参照が取得できない場合、黙ってスキップせずWARNを出す
if ho_remote is None or ho_base is None:
    print("[WARN] リモート参照（ls-remote/merge-base）を取得できません。陳腐化チェックをスキップします。")
    print("  → ネットワーク不通またはリモート未設定の可能性があります。確認してください。")

if ho_remote and ho_base and ho_head:
    # merge base で見ていた handover.md ≠ リモート → 誰かが更新している
    if ho_base != ho_remote:
        # さらに HEAD でも同じ → 自分は何も変えてない＝気づかずに古い
        if ho_head == ho_base:
            print(f"[BLOCK] handover.md がリモートで更新されています。")
            print(f"  → 'git pull' して handover.md を再読してください。")
            sys.exit(1)

# handover.md 更新時の session_log 整合性チェック
if ho_head and ho_base and ho_head != ho_base and os.path.isdir("knowledge/session_log/"):
    try:
        with open("knowledge/handover.md", "r", encoding="utf-8") as f:
            content = f.read()
        entries = re.findall(r'\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*\*{0,2}(.+?)\*{0,2}\s*\|\s*(.+?)\s*\|', content)
        for date, session, highlight in entries:
            dc = date.replace("-", "")
            matches = [f for f in os.listdir("knowledge/session_log/") if dc in f]
            if not matches:
                print(f"[WARN] handover.md に記載があるのに session_log が見つかりません: {date} {session.strip()}")
    except Exception:
        pass

# coreファイル差分表示（ブロックしない）
for cf in CORE_FILES:
    loc_remote_diff = subprocess.run(["git", "diff", "--stat", f"origin/main", "HEAD", "--", cf],
                                     capture_output=True, text=True)
    if loc_remote_diff.stdout.strip():
        print(f"[INFO] {cf}: リモートとローカルで内容が異なります:")
        for line in loc_remote_diff.stdout.strip().splitlines():
            print(f"  {line}")

# handover.md 更新なし警告（セッション終了時の更新忘れ検知）
if ho_head and ho_base and ho_head == ho_base:
    # handover.md がローカルで未変更。pushするコミットに更新が含まれているか確認
    new_commits = subprocess.run(["git", "rev-list", f"origin/main..HEAD"],
                                 capture_output=True, text=True)
    if new_commits.stdout.strip():
        ho_in_commits = subprocess.run(["git", "diff", "--name-only", f"origin/main..HEAD", "--", "knowledge/handover.md"],
                                       capture_output=True, text=True)
        if not ho_in_commits.stdout.strip():
            print(f"[WARN] handover.md の更新がありません。セッション終了時に更新しましたか？")

sys.exit(0)
