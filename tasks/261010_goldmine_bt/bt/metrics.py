"""指標: 総リターン、最大DD、勝率、平均損益、取引数、コスト合計。正直計算のみ。"""


def compute(equity_curve, trades, total_cost, initial_capital):
    eq = [p["equity"] for p in equity_curve]
    final = eq[-1] if eq else initial_capital
    total_return = (final - initial_capital) / initial_capital if initial_capital else 0.0
    peak = eq[0] if eq else initial_capital
    max_dd = 0.0
    for v in eq:
        if v > peak:
            peak = v
        dd = (peak - v) / peak if peak else 0.0
        if dd > max_dd:
            max_dd = dd
    n = len(trades)
    wins = sum(1 for t in trades if t["net"] > 0)
    win_rate = wins / n if n else 0.0
    avg_pnl = sum(t["net"] for t in trades) / n if n else 0.0
    gross_profit = sum(t["net"] for t in trades if t["net"] > 0)
    gross_loss = -sum(t["net"] for t in trades if t["net"] <= 0)
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float("inf") if gross_profit > 0 else 0.0
    return {
        "final_equity": final,
        "total_return": total_return,
        "max_dd": max_dd,
        "win_rate": win_rate,
        "avg_pnl": avg_pnl,
        "n_trades": n,
        "total_cost": total_cost,
        "profit_factor": profit_factor,
    }
