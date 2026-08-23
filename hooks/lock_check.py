"""楽観的ロック: ロック状態確認"""
import sys, os, json
LOCK_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".locks")

def lock_path(filepath):
    safe = filepath.replace("\\", "/").replace("/", "_").replace(".", "_")
    return os.path.join(LOCK_DIR, safe + ".lock")

def main():
    if len(sys.argv) < 2:
        targets = [t for t in os.listdir(LOCK_DIR) if t.endswith(".lock")] if os.path.exists(LOCK_DIR) else []
        print(f"アクティブロック: {len(targets)}")
        for t in targets:
            with open(os.path.join(LOCK_DIR, t), "r", encoding="utf-8") as f:
                print(f"  {json.load(f)['file']}")
        return
    fp = sys.argv[1]
    lp = lock_path(fp)
    if not os.path.exists(lp):
        print(f"[LOCK] ロックされていません: {fp}")
        sys.exit(0)
    with open(lp, "r") as f:
        data = json.load(f)
    print(f"[LOCK] ロック中: {fp}")
    for k, v in data.items():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
