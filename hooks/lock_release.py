"""楽観的ロック: ファイルロック解放"""
import sys, os, json
LOCK_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".locks")

def lock_path(filepath):
    safe = filepath.replace("\\", "/").replace("/", "_").replace(".", "_")
    return os.path.join(LOCK_DIR, safe + ".lock")

def main():
    if len(sys.argv) < 2:
        print("Usage: lock_release.py <filepath>")
        sys.exit(1)
    fp = sys.argv[1]
    lp = lock_path(fp)
    if not os.path.exists(lp):
        print(f"[LOCK] ロックされていません: {fp}")
        sys.exit(0)
    os.remove(lp)
    print(f"[LOCK] ロック解放: {fp}")

if __name__ == "__main__":
    main()
