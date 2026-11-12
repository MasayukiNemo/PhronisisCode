"""model_watch.py — OpenCode のモデル一覧から、無料・大文脈の候補表を出す。

使い方:
  python scripts/model_watch.py [--free-only] [--min-context 1000000] [--json] [--out PATH]

データ源: OpenCode アプリの /api/model（service.json の password で Basic 認証）。
取れる項目: provider / model / name / cost(input,output, USD/1M) / context / output / tools / status / enabled。
取れない項目: キャンペーン期間（公式X @opencode が一次情報）。

注意: 切り替えは自動でしない。大きな開発の前に、候補表と公式Xの告知を突き合わせて検討する。
"""

import argparse
import base64
import json
import os
import sys
import urllib.request
from pathlib import Path

SERVICE_JSON = Path(os.environ.get("USERPROFILE", str(Path.home()))) / ".config" / "opencode" / "service.json"
DEFAULT_BASE = "http://127.0.0.1:28894"


def load_password():
    try:
        return json.loads(SERVICE_JSON.read_text(encoding="utf-8")).get("password")
    except (OSError, ValueError):
        return None


def fetch_models(base):
    password = load_password()
    if not password:
        raise RuntimeError(f"password not found in {SERVICE_JSON}")
    req = urllib.request.Request(
        base + "/api/model",
        headers={"Authorization": "Basic " + base64.b64encode(f"opencode:{password}".encode()).decode()},
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=15) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data.get("data", [])


def cost_of(model):
    cost = (model.get("cost") or [{}])[0]
    return float(cost.get("input") or 0), float(cost.get("output") or 0)


def collect(models):
    rows = []
    for model in models:
        if not model.get("enabled", False):
            continue
        if model.get("type") != "chat":
            continue
        caps = model.get("capabilities") or {}
        if not caps.get("tools"):
            continue
        cost_in, cost_out = cost_of(model)
        limit = model.get("limit") or {}
        rows.append(
            {
                "provider": model.get("providerID"),
                "model": model.get("modelID"),
                "name": model.get("name"),
                "cost_in": cost_in,
                "cost_out": cost_out,
                "free": cost_in == 0 and cost_out == 0,
                "context": int(limit.get("context") or 0),
                "output": int(limit.get("output") or 0),
                "status": model.get("status"),
            }
        )
    rows.sort(key=lambda r: (not r["free"], -r["context"], r["cost_in"]))
    return rows


def markdown(rows, min_context):
    free = [r for r in rows if r["free"]]
    large = [r for r in rows if r["context"] >= min_context]
    lines = ["# OpenCode モデル候補表", ""]

    lines += ["## 無料モデル（cost=0）", ""]
    lines.append("| provider | model | name | cost in/out | context | output |")
    lines.append("|---|---|---|---|---|---|")
    for r in free:
        lines.append(
            f"| {r['provider']} | {r['model']} | {r['name']} | 0 / 0 | {r['context']:,} | {r['output']:,} |"
        )
    if not free:
        lines.append("| - | - | - | - | - | - |")

    lines += ["", f"## 大文脈モデル（context >= {min_context:,}）", ""]
    lines.append("| provider | model | name | cost in/out | context | output | free |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in large:
        lines.append(
            f"| {r['provider']} | {r['model']} | {r['name']} | {r['cost_in']} / {r['cost_out']} | "
            f"{r['context']:,} | {r['output']:,} | {'yes' if r['free'] else ''} |"
        )
    if not large:
        lines.append("| - | - | - | - | - | - | - |")

    lines += ["", "## 注", "", "- キャンペーン期間は API に出ない。公式X（@opencode）が一次情報。", "- 切り替えは自動でしない。大きな開発の前に候補として検討する。"]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="OpenCode モデルの候補表")
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--min-context", type=int, default=1000000)
    parser.add_argument("--free-only", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    try:
        models = fetch_models(args.base)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    rows = collect(models)
    if args.free_only:
        rows = [r for r in rows if r["free"]]

    if args.json:
        text = json.dumps(rows, ensure_ascii=False, indent=2) + "\n"
    else:
        text = markdown(rows, args.min_context)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text)
        print(f"saved: {args.out}", file=sys.stderr)
    else:
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
