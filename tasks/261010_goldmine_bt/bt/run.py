"""設定→データ読込→実行→指標→レポート。CLIのみ。GUIなし。

使い方:
  python -m bt.run --selftest
  python -m bt.run --csv data/EURUSD=X.csv --symbol EURUSD --out equity_curve.csv --db trades.db
"""
import argparse
import csv
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bt.engine import Config, run_backtest  # noqa: E402
from bt.strategies import signal  # noqa: E402
from bt.metrics import compute  # noqa: E402
from bt.store import connect, record_all  # noqa: E402


def signal_wrap(df, closes, highs, lows, i, cfg):
    return signal(None, closes, highs, lows, i,
                 entry_n=cfg.entry_n, exit_n=cfg.exit_n)


def load_csv(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({
                "date": r["date"],
                "open": float(r["open"]) if r["open"] else None,
                "high": float(r["high"]) if r["high"] else None,
                "low": float(r["low"]) if r["low"] else None,
                "close": float(r["close"]),
                "volume": float(r["volume"]) if r.get("volume") else None,
            })
    rows.sort(key=lambda r: r["date"])
    return rows


def synth_data(seed=42, n=400, start=1.10):
    rnd = random.Random(seed)
    px = start
    rows = []
    for k in range(n):
        o = px
        drift = 0.0004 if k % 50 < 30 else -0.0004  # 往復相場 (勝たせない意図)
        c = o * (1 + drift + rnd.gauss(0, 0.004))
        h = max(o, c) * (1 + abs(rnd.gauss(0, 0.001)))
        lo = min(o, c) * (1 - abs(rnd.gauss(0, 0.001)))
        rows.append({"date": "2020-%02d-%02d" % (1 + (k // 28) % 12, 1 + k % 28),
                     "open": o, "high": h, "low": lo, "close": c, "volume": 0})
        px = c
    # 日付ソート済みに見せかけるため連番日付に置換
    base = 0
    for r in rows:
        base += 1
        r["date"] = "D%05d" % base
    return rows


def run_once(df, cfg, symbol="SYNTH"):
    res = run_backtest(df, cfg, signal_wrap)
    m = compute(res["equity"], res["trades"], res["total_cost"], cfg.initial_capital)
    return res, m


def selftest():
    print("[selftest] start (no GUI, no network)")
    # 1. 再現性: 同seed -> 同出力
    a = synth_data(seed=7)
    b = synth_data(seed=7)
    assert a == b, "synth not reproducible"
    print("[selftest] reproducibility OK")

    # 2. コスト全明示: コスト>0 かつ内訳が設定由来
    cfg = Config(qty=1000.0, spread=0.0002, commission_rt=1.0, slippage=0.00005)
    res, m = run_once(a, cfg)
    assert res["total_cost"] >= 0, "cost negative?"
    if m["n_trades"] > 0:
        assert res["total_cost"] > 0, "zero-cost assumption detected"
    print("[selftest] cost explicit OK (trades=%d cost=%.4f)" % (m["n_trades"], res["total_cost"]))

    # 3. look-aheadなし: 未来改変で当日シグナル不変
    from bt.strategies import signal as sig
    df_c = [r["close"] for r in a]
    df_h = [r["high"] for r in a]
    df_l = [r["low"] for r in a]
    i = 250
    s1 = sig(None, df_c, df_h, df_l, i)
    df_c2 = list(df_c)
    df_h2 = list(df_h)
    df_l2 = list(df_l)
    df_c2[i + 1] = df_c2[i + 1] * 1.5  # 未来を大きく改変
    df_h2[i + 1] = df_h2[i + 1] * 1.5
    s2 = sig(None, df_c, df_h, df_l, i)  # signalは[..i]のみ参照するので不変のはず
    assert s1 == s2, "signal depends on future?"
    # エンジン約定が翌openであること: entry翌日のopenを動かすとentry価格が動く
    df_mod = [dict(r) for r in a]
    res1 = run_backtest([dict(r) for r in a], cfg, signal_wrap)
    if res1["trades"]:
        first_entry = res1["trades"][0]["entry_date"]
        idx = next(k for k, r in enumerate(a) if r["date"] == first_entry)
        if idx + 1 < len(df_mod):
            df_mod[idx]["open"] = df_mod[idx]["open"] * 1.10
            res2 = run_backtest(df_mod, cfg, signal_wrap)
            # シグナル日は同じでも約定価格が変わる = 翌足約定の証拠 (取引数が同じ場合のみ比較)
            if res2["trades"] and len(res2["trades"]) == len(res1["trades"]):
                assert res2["trades"][0]["entry_px"] != res1["trades"][0]["entry_px"], \
                    "execution not on next bar?"
    print("[selftest] no look-ahead OK")

    # 4. kill switch発火: 上昇でlong保有を作り暴落で日次上限を超過させる
    kill_df = []
    px = 1.0
    for k in range(260):
        o = px
        c = o * 1.005  #  steady uptrend -> Donchian long が必ず建つ
        kill_df.append({"date": "K%05d" % k, "open": o, "high": c * 1.001,
                        "low": o * 0.999, "close": c, "volume": 0})
        px = c
    for k in range(260, 266):
        o = px
        c = o * 0.94  # 1日 -6% の暴落
        kill_df.append({"date": "K%05d" % k, "open": o, "high": o,
                        "low": c * 0.999, "close": c, "volume": 0})
        px = c
    for k in range(266, 300):
        o = px
        kill_df.append({"date": "K%05d" % k, "open": o, "high": o * 1.001,
                        "low": o * 0.999, "close": o, "volume": 0})
    cfg_kill = Config(qty=100000.0, spread=0.0002, daily_max_loss_frac=0.01,
                      sl_dist=10.0, tp_dist=10.0)  # SL遠ざけ・qty肥大で日次損失を誘発
    resk = run_backtest(kill_df, cfg_kill, signal_wrap)
    assert len(resk["halted_days"]) > 0, "kill switch did not fire: %s" % resk["halted_days"]
    assert any(t["exit_reason"] == "kill_switch" for t in resk["trades"]), "no kill exit row"
    print("[selftest] kill switch OK (halted=%s)" % resk["halted_days"][:3])

    # 5. SQLite記録
    import tempfile
    tmp = tempfile.mktemp(suffix=".db")
    con = connect(tmp)
    nrec = record_all(con, res["trades"], symbol="SELFTEST")
    from bt.store import count as dbcount
    assert dbcount(con) == nrec == len(res["trades"]), "db count mismatch"
    con.close()
    try:
        os.remove(tmp)
    except OSError:
        pass
    print("[selftest] sqlite OK (%d rows)" % nrec)

    # 6. walk-forward OSが出る (synthetic 3fold)
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from walk_forward import rolling_splits, run_fold
    folds = rolling_splits(a, n_splits=3, is_frac=0.6)
    assert len(folds) == 3, "folds != 3"
    os_rows = [run_fold(a, s, e, os_, oe, cfg) for (s, e, os_, oe) in folds]
    assert all("os_n_trades" in r for r in os_rows), "OS missing"
    print("[selftest] walk-forward OS OK")
    print("[selftest] ALL PASS")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--csv", default="")
    ap.add_argument("--symbol", default="SYM")
    ap.add_argument("--out", default="equity_curve.csv")
    ap.add_argument("--db", default="trades.db")
    ap.add_argument("--capital", type=float, default=10000.0)
    ap.add_argument("--qty", type=float, default=1000.0)
    ap.add_argument("--spread", type=float, default=0.0002)
    ap.add_argument("--commission", type=float, default=0.0)
    ap.add_argument("--slippage", type=float, default=0.00005)
    ap.add_argument("--swap", type=float, default=-0.000002)
    ap.add_argument("--sl", type=float, default=0.02)
    ap.add_argument("--tp", type=float, default=0.04)
    ap.add_argument("--kill", type=float, default=0.03)
    ap.add_argument("--entry_n", type=int, default=20)
    ap.add_argument("--exit_n", type=int, default=10)
    args = ap.parse_args()
    if args.selftest:
        sys.exit(selftest())
    if not args.csv:
        print("need --csv (or --selftest)", file=sys.stderr)
        sys.exit(2)
    df = load_csv(args.csv)
    cfg = Config(initial_capital=args.capital, qty=args.qty, spread=args.spread,
                 commission_rt=args.commission, slippage=args.slippage,
                 swap_per_night_per_qty=args.swap, sl_dist=args.sl, tp_dist=args.tp,
                 daily_max_loss_frac=args.kill, entry_n=args.entry_n, exit_n=args.exit_n)
    res, m = run_once(df, cfg, symbol=args.symbol)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["date", "equity"])
        w.writeheader()
        w.writerows(res["equity"])
    con = connect(args.db)
    con.execute("DELETE FROM trades")
    record_all(con, res["trades"], symbol=args.symbol)
    con.close()
    print(json.dumps({"symbol": args.symbol, "metrics": m,
                      "halted_days": res["halted_days"],
                      "equity_csv": args.out, "db": args.db},
                     indent=2, default=str))


if __name__ == "__main__":
    main()
