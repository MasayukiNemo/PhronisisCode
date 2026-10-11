# タスク: 261010_goldmine_bt — コスト込みFXバックテスト装置（最小）

## 目的
FX（Axiory nano＝FX/CFD）でエッジを検証する第一歩。実弾は使わない。
まず「計測が正しい」バックテスト装置を作り、単純戦略1本で walk-forward の結果を出す。
勝ちを主張しない。計測の正しさがこのタスクの目的。「動く」と「勝つ」を分離する。

## 成果物（すべて `tasks/261010_goldmine_bt/` 配下。単一HTMLではなくPython実装）
- `data/fetch.py`: Yahoo Finance chart API（`https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=...&interval=1d`、`User-Agent` ヘッダ必須）から日足OHLCを取得しCSV保存（`EURUSD=X`, `USDJPY=X`）。取得失敗時は握りつぶさず明確なエラー。`frankfurter.app` を使ったクロスチェック関数も添える（daily close）。
- `bt/engine.py`: イベントドリブンのバックテスト。コストをすべて明示（spread往復・手数料・スワップ概算・slippageは設定値）。ポジションサイズ、SL/TP、日次損失上限（kill switch）、最大ポジション数。**look-ahead禁止**（シグナルは当日終値までで確定→翌足で約定）。
- `bt/strategies.py`: 単純トレンドフォロー1本（移動平均クロス か ドンチャン）。自由度は2〜3に抑える。
- `bt/run.py`: 設定→データ読込→実行→指標→レポート。`--selftest` でGUIなしの自己テスト。
- `bt/metrics.py`: 総リターン、最大DD、勝率、平均損益、取引数、コスト合計。
- `bt/store.py`: 全取引をSQLite（`trades.db`）に記録（時刻・特徴量・判断・結果・コスト）。将来の較正ラベルの燃料。
- `walk_forward.py`: IS/OS分割（例: 3分割ローリング）。**OS（アウトサンプル）結果を必ず出す**。
- `report.md`（実行結果の正直な要約）と `equity_curve.csv`。
- `README.md`（実行手順）と `run.bat`（ダブルクリックで回る＝起動のしやすさ。`--selftest` と本実行のメニュー）。
- `requirements.txt`（追加依存のみ）。

## 成功基準（自己検証で確認し、log.md に結果を書く）
- [必須] `data/fetch.py` が再現可能に動く（同入力→同出力）
- [必須] コストが全明示。ゼロコスト仮定が無い
- [必須] look-ahead なし（根拠をコード/コメントで説明。シグナル確定後に約定）
- [必須] walk-forward のOS結果が出る
- [必須] SQLite に全取引が記録される
- [必須] kill switch（日次損失上限）が実装され、`--selftest` で発火を確認
- [必須] `README` / `run.bat` で誰でも回せる
- [必須] `--selftest` がGUI無しで通り、終了コード0
- [任意] equity curve PNG

## 制約
- 実弾・API発注・ネット取引は一切しない（バックテストのみ）。ネットはデータ取得のみ。
- 会社のデータを使わない。個人・自宅環境で完結。
- 勝ちを主張しない。指標は正直に。損益を良く見せる操作（過剰最適化・未来情報・コスト無視）を禁止。
- 依存は pandas / numpy / matplotlib（導入済み）。追加は最小限。Python 3.11。
- モデルは既定の Muse（free）。有料モデルを使わない。
- GUIアプリの実行は禁止（tkinter等でブロックする）。CLIのみ。

## 手順（PhronisisCodeの流儀）
1. plan.md に設計と手順を書く（過剰設計しない。最小で動く）。
2. 実装（ダイダロス相当の作業）→ 自己検証（`--selftest` 実行、実際のデータで1回通す）。
3. Hayatoゲート4点（仕様逸脱 / 致命傷 / 手続き違反 / 軌跡品質）を自分で当て、指摘を反映。
4. log.md に軌跡（やったこと・検証結果・残課題）を書く。
5. `git add` → `git commit`（pushはしない）。

## フッタ
log.md の末尾に `<!-- status: complete | agent: kai -->` を付す。

## 注意（過去の反省）
- ユーザーが直接使う道具は「起動のしやすさ」（bat・README・オプション説明）を成功基準に含める。
- 大きいタスクで途中停止したら、未完成部分を正直に log.md に書く（空欄で「完了」と偽らない）。
