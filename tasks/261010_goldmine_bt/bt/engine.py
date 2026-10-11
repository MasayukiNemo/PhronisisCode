"""イベントドリブンの最小バックテストエンジン.

look-ahead禁止の根拠:
  - signal は i 日終値確定後に呼び (参照は closes/highs/lows の [..i] のみ)、
    約定は i+1 日 open で行う。エンジンは signal に i+1 以降を渡さない。
  - SL/TP は entry 後のバーの high/low で判定する逆指値 (因果律内)。
  - exit シグナルも entry と同じく翌 open 約定 (pending_exit)。
コスト全明示 (ゼロコスト仮定なし):
  - spread_rt: 往復スプレッド (価格単位)。entry 時に qty 倍して一括計上。
  - commission_rt: 往復手数料 (口座通貨単位)。entry 時に計上。
  - slippage: 片道の滑り (価格単位)。entry/exit の約定価格を悪化させる。
  - swap_per_night_per_qty: 1単位あたり一晩のスワップ概算 (マイナス=支払)。
"""
import json


class Config:
    def __init__(self, initial_capital=10000.0, qty=1000.0,
                 spread=0.0002, commission_rt=0.0, slippage=0.00005,
                 swap_per_night_per_qty=-0.000002,
                 sl_dist=0.02, tp_dist=0.04,
                 daily_max_loss_frac=0.03, max_positions=1,
                 entry_n=20, exit_n=10):
        """sl_dist/tp_dist は entry価格に対する相対比率 (0.02=2%)。通貨ペアの価格桁に依存しない。"""
        self.initial_capital = initial_capital
        self.qty = qty
        self.spread = spread
        self.commission_rt = commission_rt
        self.slippage = slippage
        self.swap_per_night_per_qty = swap_per_night_per_qty
        self.sl_dist = sl_dist
        self.tp_dist = tp_dist
        self.daily_max_loss_frac = daily_max_loss_frac
        self.max_positions = max_positions
        self.entry_n = entry_n
        self.exit_n = exit_n


def run_backtest(df, cfg, signal_fn):
    """df: list of dict(date,open,high,low,close). 戻り値 dict.

    trades 要素: entry_date, exit_date, side, qty, entry_px, exit_px,
      gross, cost, net (=gross-cost, 参考値), exit_reason, features_json
    equity: list of {date, equity}. final_equity = initial + realized + swap - total_cost (+未実現0).
    """
    n = len(df)
    if n == 0:
        raise ValueError("empty df")
    closes = [r["close"] for r in df]
    highs = [r["high"] if r["high"] is not None else r["close"] for r in df]
    lows = [r["low"] if r["low"] is not None else r["close"] for r in df]
    opens = [r["open"] if r["open"] is not None else r["close"] for r in df]

    realized = 0.0
    total_cost = 0.0
    swap_acc = 0.0
    trades = []
    curve = []
    pos = None
    pending_entry = False  # 前日終値で確定した entry を当日 open で約定
    pending_exit = False   # 前日終値で確定した exit を当日 open で約定
    halt_until = None
    halted_days = []
    day_start_equity = cfg.initial_capital
    cur_day = df[0]["date"]

    for i in range(n):
        date = df[i]["date"]
        if date != cur_day:
            cur_day = date
            # 日替わり時点の equity を基準にする (未実現込み)
            u = (closes[i - 1] - pos["entry_px"]) * pos["qty"] if pos is not None else 0.0
            day_start_equity = cfg.initial_capital + realized + swap_acc - total_cost + u
        halted = halt_until is not None and date <= halt_until

        # --- kill switch: 当日の未実現込み日次損が上限超過なら当日closeで全決済 ---
        unreal = (closes[i] - pos["entry_px"]) * pos["qty"] if pos is not None else 0.0
        day_pnl = (cfg.initial_capital + realized + swap_acc + unreal - total_cost) - day_start_equity
        if pos is not None and day_pnl < -cfg.daily_max_loss_frac * day_start_equity:
            exit_px = closes[i] - cfg.slippage
            gross = (exit_px - pos["entry_px"]) * pos["qty"]
            realized += gross
            trades.append({
                "entry_date": pos["entry_date"], "exit_date": date,
                "side": "long", "qty": pos["qty"],
                "entry_px": pos["entry_px"], "exit_px": exit_px,
                "gross": gross, "cost": pos["entry_cost"],
                "net": gross - pos["entry_cost"],
                "exit_reason": "kill_switch",
                "features_json": json.dumps({"entry_n": cfg.entry_n, "exit_n": cfg.exit_n}),
            })
            pos = None
            pending_entry = False
            pending_exit = False
            halt_until = df[i + 1]["date"] if i + 1 < n else date
            halted_days.append(date)
            equity = cfg.initial_capital + realized + swap_acc - total_cost
            curve.append({"date": date, "equity": equity})
            continue

        # --- 約定 (当日 open。前日終値シグナルのみ) ---
        if pending_exit and pos is not None:
            exit_px = opens[i] - cfg.slippage
            gross = (exit_px - pos["entry_px"]) * pos["qty"]
            realized += gross
            trades.append({
                "entry_date": pos["entry_date"], "exit_date": date,
                "side": "long", "qty": pos["qty"],
                "entry_px": pos["entry_px"], "exit_px": exit_px,
                "gross": gross, "cost": pos["entry_cost"],
                "net": gross - pos["entry_cost"],
                "exit_reason": "exit_signal",
                "features_json": json.dumps({"entry_n": cfg.entry_n, "exit_n": cfg.exit_n}),
            })
            pos = None
            pending_exit = False
        if pending_entry and pos is None and not halted:
            entry_px = opens[i] + cfg.slippage
            entry_cost = cfg.spread * cfg.qty + cfg.commission_rt
            total_cost += entry_cost
            pos = {"entry_date": date, "entry_px": entry_px,
                   "sl": entry_px * (1 - cfg.sl_dist), "tp": entry_px * (1 + cfg.tp_dist),
                   "qty": cfg.qty, "entry_cost": entry_cost}
        pending_entry = False

        # --- 保有中の SL/TP (entry バー以降の intrabar。SL優先の保守評価) ---
        if pos is not None and pos["entry_date"] != date:
            if lows[i] <= pos["sl"]:
                exit_px = pos["sl"] - cfg.slippage
                reason = "stop_loss"
            elif highs[i] >= pos["tp"]:
                exit_px = pos["tp"] - cfg.slippage
                reason = "take_profit"
            else:
                exit_px, reason = None, None
            if reason is not None:
                gross = (exit_px - pos["entry_px"]) * pos["qty"]
                realized += gross
                trades.append({
                    "entry_date": pos["entry_date"], "exit_date": date,
                    "side": "long", "qty": pos["qty"],
                    "entry_px": pos["entry_px"], "exit_px": exit_px,
                    "gross": gross, "cost": pos["entry_cost"],
                    "net": gross - pos["entry_cost"],
                    "exit_reason": reason,
                    "features_json": json.dumps({"entry_n": cfg.entry_n, "exit_n": cfg.exit_n}),
                })
                pos = None
                pending_exit = False

        # --- シグナル確定 (当日終値まで。約定は翌 open) ---
        if i + 1 < n:
            sig = signal_fn(df, closes, highs, lows, i, cfg)
            if pos is not None and sig == -1:
                pending_exit = True
            elif pos is None and sig == 1 and not halted:
                pending_entry = True

        # --- overnight swap 概算 (保有したまま跨ぐ夜) ---
        if pos is not None and i + 1 < n:
            swap_acc += cfg.swap_per_night_per_qty * cfg.qty

        equity = cfg.initial_capital + realized + swap_acc - total_cost
        if pos is not None:
            equity += (closes[i] - pos["entry_px"]) * pos["qty"]
        curve.append({"date": date, "equity": equity})

    if pos is not None:
        exit_px = closes[-1] - cfg.slippage
        gross = (exit_px - pos["entry_px"]) * pos["qty"]
        realized += gross
        trades.append({
            "entry_date": pos["entry_date"], "exit_date": df[-1]["date"],
            "side": "long", "qty": pos["qty"],
            "entry_px": pos["entry_px"], "exit_px": exit_px,
            "gross": gross, "cost": pos["entry_cost"],
            "net": gross - pos["entry_cost"],
            "exit_reason": "final_close",
            "features_json": json.dumps({"entry_n": cfg.entry_n, "exit_n": cfg.exit_n}),
        })
        equity = cfg.initial_capital + realized + swap_acc - total_cost
        curve[-1] = {"date": df[-1]["date"], "equity": equity}

    return {"equity": curve, "trades": trades, "total_cost": total_cost,
            "swap": swap_acc, "halted_days": halted_days,
            "final_equity": equity}
