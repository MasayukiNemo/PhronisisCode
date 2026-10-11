# plan.md — 261010_goldmine_bt コスト込みFXバックテスト装置（最小）

## 1. 目的の再確認
- 「計測が正しい」装置を作る。勝ちの主張はしない。
- 単一戦略で walk-forward の OS 結果を出す。動くと勝つを分離。

## 2. 前提検証
- Python 3.11.1 確認済み。pandas 2.0.1 / numpy 1.26.4 (2.4.6から downgrade し互換性修復) / matplotlib 3.7.1 / requests 2.34.2。
- ネットは Yahoo chart API と frankfurter のみ。発注なし。
- トライアングル簡略: 仕様確定済み・確信高のため深層思考のみ。Yuna照合=曖昧さなし (対象2通貨・日足・コスト明示)。Hayato中間=仕様逸脱なし。
- 招集判断: 6神なしで直接実装。理由: 設計案は単一 (MA cross)、未知調査なし (Yahoo API は既知形式)、変更は新規7ファイルだが依存は直線 (fetch→engine→run→walk_forward) で判断不要、バグ・レビュー指摘なし。呼ばなかった理由をここに記録。

## 3. 設計 (最小)
- data/: fetch.py が Yahoo `query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5y&interval=1d` に User-Agent 付き GET。JSON → DataFrame(date,open,high,low,close,volume) → CSV `data/EURUSD=X.csv` 等。失敗は例外送出 (握りつぶし禁止)。`frankfurter_crosscheck(date, base, quote)` が `api.frankfurter.app/{date}?from=&to=` の daily close を返す。
- bt/strategies.py: Donchian ブレイク (自由度2: entry_n=20, exit_n=10) + SMA200 フィルタは固定 (自由度に数えない)。signal(df, i) は i 日終値までのみ参照。
- bt/engine.py: イベントループ。i 日終値で signal 確定 → 翌日 (i+1) 始値... ではなく翌日 open で約定 (データが open を持つため。open 無ければ当日 close+slippage)。コスト = spread往復 + commission + slippage + swap(overnight 日数×rate)。SL/TP は約定価格基準。kill switch: 日次 equity が前日比 -daily_max_loss を超えたら当日残り+翌日停止。max_positions=1 固定で複雑さ排除。long/short 両対応。
- bt/metrics.py: total_return, max_dd, win_rate, avg_pnl, n_trades, total_cost, profit_factor。
- bt/store.py: sqlite3 標準のみ。`trades.db` table trades(entry_date,exit_date,symbol,side,qty,entry_px,exit_px,gross_pnl,cost,net_pnl,exit_reason,features_json)。
- bt/run.py: argparse (symbol/csv/lot/spread/commission/slippage/swap/sl_tp/kill/out)。`--selftest` は合成データ (seed固定のランダムウォーク 300本) で kill発火・look-ahead・DB記録・コスト>0・metrics整合を assert。GUI import 禁止 (matplotlib は Agg のみ、tkinter 不使用)。
- walk_forward.py: CSV を時系列3分割ローリング (IS 60% / OS 40% を3回スライド)。各 fold で run_backtest → OS 指標を集計し stdout + `os_results.csv`。OS 必須出力。
- 成果物: report.md (正直要約・数値は実測転記)、equity_curve.csv (date,equity)、README.md、run.bat (1=selftest 2=fetch 3=run 4=walkforward)、requirements.txt (requests のみ。pandas/numpy/matplotlib は導入済みのため記載分離)。

## 4. 手順
1. plan.md (本書)
2. 実装 7ファイル + README/run.bat/requirements
3. `python -m bt.run --selftest` (終了コード0確認)
4. `python data/fetch.py` (実データ取得。失敗時は合成フォールバックを明示)
5. `python -m bt.run` + `python walk_forward.py` (実データで1回通す)
6. Hayato ゲート4点自己適用 → 修正反映
7. log.md + report.md + git add/commit (pushなし)

## 5. やらないこと
- 最適化ループ、パラメータ探索、PNG 必須化 (任意扱い)、GUI、live 発注。
