# report.md — 実行結果の正直な要約 (261010_goldmine_bt)

勝ちを主張しない。数値は実測転記。良く見せる操作なし。

## 条件
- データ: Yahoo 日足 5y (EURUSD=X 1301 rows, USDJPY=X 1301 rows)。`python data/fetch.py` で取得。
- 戦略: Donchian ブレイク (entry_n=20, exit_n=10) + SMA200 フィルタ、long のみ。
- コスト: spread 0.0002 往復、commission 0、slippage 0.00005 片道、swap -0.000002/単位/夜。qty=1000、初期 10000。
- SL/TP: entry 価格の 2% / 4% (相対。絶対値の桁依存を避ける)。
- 約定: シグナルは当日終値確定 → 翌 open 約定。SL/TP は逆指値 intrabar。

## フル期間
- EURUSD: ret -0.82%, maxDD 1.28%, win 40.0%, avg -5.44, n=15, cost 3.0, PF 0.235, kill発火 0日。
- USDJPY: ret +38.06%, maxDD 38.72%, win 41.7%, avg +158.60, n=24, cost 4.8, PF 1.305, kill発火 23日。

## walk-forward OS (3分割ローリング)
- EURUSD: fold0 OS 1 trade ret -0.23% / fold1 OS 2 trades ret -0.10% / fold2 OS 0 trades ret 0%。
- USDJPY: fold0 OS 1 trade ret -18.04% / fold1 OS 5 trades ret -4.03% / fold2 OS 0 trades ret 0%。

## 正直な読み
- EURUSD はコスト込みでマイナス。エッジなし。
- USDJPY のフル期間 +38% は IS に引っ張られた見かけであり、OS では再現しない (fold0 -18%、fold1 -4%)。IS/OS 乖離 = 汎化なしと読む。フル期間のプラスを根拠に使わない。
- fold2 (直近) は両通貨とも取引 0。ブレイク条件が直近相場に合っていない。無取引も結果として記録する (取引させる調整はしない)。
- kill switch は USDJPY で 23日発火し機能した。EURUSD では発火なし (損失が上限未満)。

## クロスチェック
- frankfurter 2024-01-02 EUR/USD = 1.0956 を取得。Yahoo 終値との突合は目視未実施 (残課題)。

## 残課題
- equity curve PNG は未作成 (任意項目。CLI の `equity_curve.csv` で代替)。
- パラメータ探索なし (意図的にやらない。過剰最適化の禁止)。
