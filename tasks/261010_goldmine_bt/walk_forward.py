"""walk-forward: IS/OS分割 (3分割ローリング)。OS結果を必ず出す。CLIのみ。

使い方:
  python walk_forward.py --csv data/EURUSD=X.csv --symbol EURUSD
  python walk_forward.py --synth   (データが無い場合の合成フォールバック)
"""
import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bt.engine import Config  # noqa: E402
from bt.run import load_csv, run_once, synth_data  # noqa: E402


def rolling_splits(df, n_splits=3, is_frac=0.6):
    n = len(df)
    chunk = n // (n_splits + 1)
    folds = []
    for k in range(n_splits):
        s = k * chunk
        e = s + chunk + int(chunk * is_frac)
        os_ = e
        oe = min(e + chunk, n)
        if oe - os_ < 10:
            break
        folds.append((s, e, os_, oe))
    return folds


def run_fold(df, s, e, os_, oe, cfg):
    is_df, os_df = df[s:e], df[os_:oe]
    _, m_is = run_once(is_df, cfg)
    _, m_os = run_once(os_df, cfg)
    return {"is_n_trades": m_is["n_trades"], "is_return": m_is["total_return"],
            "os_n_trades": m_os["n_trades"], "os_return": m_os["total_return"],
            "os_max_dd": m_os["max_dd"], "os_win_rate": m_os["win_rate"],
            "os_avg_pnl": m_os["avg_pnl"], "os_cost": m_os["total_cost"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="")
    ap.add_argument("--symbol", default="SYM")
    ap.add_argument("--synth", action="store_true")
    ap.add_argument("--out", default="os_results.csv")
    args = ap.parse_args()
    if args.synth or not args.csv:
        df = synth_data(seed=42)
        symbol = "SYNTH"
    else:
        df = load_csv(args.csv)
        symbol = args.symbol
    cfg = Config()
    folds = rolling_splits(df, n_splits=3, is_frac=0.6)
    if not folds:
        print("not enough data for walk-forward", file=sys.stderr)
        sys.exit(2)
    rows = []
    for k, (s, e, os_, oe) in enumerate(folds):
        r = run_fold(df, s, e, os_, oe, cfg)
        r["fold"] = k
        r["symbol"] = symbol
        rows.append(r)
        print("fold %d IS[%d:%d] n=%d ret=%.4f | OS[%d:%d] n=%d ret=%.4f dd=%.4f win=%.3f" % (
            k, s, e, r["is_n_trades"], r["is_return"], os_, oe,
            r["os_n_trades"], r["os_return"], r["os_max_dd"], r["os_win_rate"]))
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["fold", "symbol", "is_n_trades", "is_return",
                                          "os_n_trades", "os_return", "os_max_dd",
                                          "os_win_rate", "os_avg_pnl", "os_cost"])
        w.writeheader()
        w.writerows(rows)
    print(json.dumps({"symbol": symbol, "folds": rows}, indent=2))
    print("OS results -> %s" % args.out)


if __name__ == "__main__":
    main()
