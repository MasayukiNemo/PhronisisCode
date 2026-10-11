# goldmine-bt — コスト込みFXバックテスト装置（最小）

CLIのみ。GUIなし。発注なし。バックテストとデータ取得だけ。

## 準備

  pip install -r requirements.txt

pandas / numpy / matplotlib は導入済み想定。追加は requests のみ。
実際は標準ライブラリ (urllib) で取得するため requests は未使用でも動く。

## 実行手順

1. 自己テスト (GUIなし):

  python -m bt.run --selftest

終了コード0で PASS。

2. データ取得 (Yahoo Finance 日足):

  python data/fetch.py

`data/EURUSD=X.csv` と `data/USDJPY=X.csv` ができる。
取得失敗時は明確なエラーで停止する (握りつぶさない)。

3. バックテスト1回:

  python -m bt.run --csv data/EURUSD=X.csv --symbol EURUSD --out equity_curve.csv --db trades.db

4. walk-forward (OS必須出力):

  python walk_forward.py --csv data/EURUSD=X.csv --symbol EURUSD --out os_results.csv

データが無い場合は `--synth` で合成データで回せる (計測装置の動作確認用)。

## コスト

spread往復・commission往復・slippage片道・swap概算をすべて明示。
ゼロコスト仮定なし。設定は `bt/run.py --help` を参照。

## look-ahead

シグナルは当日終値までで確定し約定は翌足 open。コード根拠は `bt/engine.py` の
pending_entry / pending_exit と `bt/strategies.py` の signal コメント。
