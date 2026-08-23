"""楽観的ロック: ファイルロック取得"""
import sys, os, json, time
LOCK_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".locks")

def lock_path(filepath):
    safe = filepath.replace("\\", "/").replace("/", "_").replace(".", "_")
    return os.path.join(LOCK_DIR, safe + ".lock")

def main():
    if len(sys.argv) < 2:
        print("Usage: lock_acquire.py <filepath> [purpose]")
        sys.exit(1)
    fp = sys.argv[1]
    purpose = sys.argv[2] if len(sys.argv) > 2 else "edit"
    os.makedirs(LOCK_DIR, exist_ok=True)
    lp = lock_path(fp)
    if os.path.exists(lp):
        with open(lp, "r") as f:
            data = json.load(f)
        print(f"[LOCK] 既にロックされています: {fp}")
        print(f"  所有者: {data['owner']} | TTL: {data['ttl_seconds']}s | 獲得: {data['acquired_at']}")
        sys.exit(1)
    lock = {
        "file": fp,
        "owner": os.environ.get("USERNAME") or os.environ.get("USER") or "unknown",
        "purpose": purpose,
        "acquired_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "ttl_seconds": 1800,
        "heartbeat_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "status": "active"
    }
    with open(lp, "w", encoding="utf-8") as f:
        json.dump(lock, f, ensure_ascii=False, indent=2)
    print(f"[LOCK] ロック獲得: {fp} (purpose={purpose}, TTL=1800s)")

if __name__ == "__main__":
    main()
