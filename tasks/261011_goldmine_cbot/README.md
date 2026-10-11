# GoldmineProbe — cTrader デモ発注プローブ

目的: Axioryデモで「注文が実際に飛ぶ」を確認する最小cBot。既定では発注しない。戦略は含まない。

## 入れ方

1. cTraderを開く
2. 下部の Automate タブを開く
3. 左ペインで cBot を右クリック → 新規cBot → 名前 GoldmineProbe
4. tasks/261011_goldmine_cbot/GoldmineProbe.cs の全文を貼付けて保存
5. Build を押してエラー0を確認
6. デモ口座にログインしている事を確認（実弾口座では使わない）
7. 対象チャート（例: EURUSD / USDJPY）にcBotをドラッグ
8. パラメータを設定して実行

## パラメータ

| 名前 | 既定 | 意味 |
|------|------|------|
| Enable Order | false | trueの時だけ1回発注。既定は接続確認のみ |
| Volume (lots) | 0.01 | 発注ロット |
| Stop Loss (pips) | 20 | 損切りpips |
| Take Profit (pips) | 40 | 利確pips |
| Max Spread (pips) | 2.0 | これを超えるスプレッドでは発注見送り |
| Max Daily Loss (account ccy) | 50 | 当日Equity下落がこの額を超えたら新規停止＋全決済＋停止 |

## 動作

- 起動時にデモ口座か検査する。デモ以外なら ABORT をPrintして Stop する
- 口座番号 / ブローカー / 種別 / 残高 / 銘柄 / スプレッド（生値とpips換算）をPrintする
- EnableOrder=false なら発注しない
- EnableOrder=true ならスプレッドが MaxSpreadPips 以内の時だけ Buy を1回発注する。結果（IsSuccessful / Error / EntryPrice）とスリッページ（約定 - 発注前Ask）をPrintする。フラグで1回に固定し、OnTickでは発注しない
- OnTickはkill switchのみ。当日Equity - 当日起動時Equity が -MaxDailyLoss を超えたら全ポジション決済して Stop する
- 終了時に OrderAttempted / KillSwitched をPrintする

## トラブルシュート

- Buildエラー: 貼付け漏れを確認。namespace cAlgo.Robots と using cAlgo.API が先頭にあるか確認
- ABORT: not a demo account: 実弾口座に付けている。デモ口座に切替える
- SKIP: spread exceeds: 時間帯を変えるか MaxSpreadPips を緩める（デモ確認用の一時措置に留める）
- Order FAILED: Error=...: そのError名をログに残し、Volume/ストップ距離/営業時間を見直す
- KILL-SWITCH発動: 当日損失が上限到達。全決済後に停止する仕様。ログの日次P/Lを確認
- Position is null: 成功扱いだが約定参照が取れなかった。ログのPreBid/PreAskを残して再現確認

## 安全注意

- live / 実弾口座には触れない
- 初回は EnableOrder=false で接続とスプレッド表示を確認してから true にする
- cTrader 5.1 / 5.6 両対応のため安定した慣用のみ使用
