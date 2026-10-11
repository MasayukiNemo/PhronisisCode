# タスク: 261011_goldmine_cbot — cTrader用デモ発注プローブ cBot

## 目的
cTrader（Axioryデモ）で「注文が実際に飛ぶ」を確認する最小 cBot。安全第一（デモ限定ガード・kill switch）。戦略はまだ入れない（次段）。

## 成果物（すべて `tasks/261011_goldmine_cbot/` 配下）
- `GoldmineProbe.cs`（cBot本体・単一ファイル）
- `README.md`（cTraderへの入れ方・パラメータ説明・トラブルシュート）
- `log.md`（軌跡・検証・残課題。末尾にフッタ `<!-- status: complete | agent: kai -->`）

## cBot 仕様（cAlgo API を正しく使うこと。下記の慣用に従う）
- 名前空間/属性: `using cAlgo.API;` `namespace cAlgo.Robots { [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.None)] public class GoldmineProbe : Robot { ... } }`
- パラメータ（`[Parameter(...)]`）:
  - `EnableOrder` (bool, 既定 false)
  - `Volume` (double, 既定 0.01)
  - `StopLossPips` (double, 既定 20)
  - `TakeProfitPips` (double, 既定 40)
  - `MaxSpreadPips` (double, 既定 2.0)
  - `MaxDailyLoss` (double, 既定 50。口座通貨建て)
- `OnStart()`:
  1. デモ判定（ハードガード）: `if (Account.AccountType != AccountType.Demo) { Print("ABORT: not a demo account ({0})", Account.AccountType); Stop(); return; }`
  2. Print で `Account.Number` / `Account.BrokerName` / `Account.AccountType` / `Account.Balance` / `Symbol.Name` / `Symbol.Spread`（pips換算 = `Symbol.Spread / Symbol.PipSize`）を出す。
  3. `EnableOrder == true` のときだけ、`MaxSpreadPips` 以内なら `ExecuteMarketOrder(TradeType.Buy, Symbol.Name, Volume, "goldmine-probe", StopLossPips, TakeProfitPips)` を1回実行。戻り `TradeResult` の `.IsSuccessful` / `.Error` / `.Position.EntryPrice` を Print。スリッページ（発注時の中値や Bid/Ask と約定の差）も Print。フラグで1回だけに固定。
  4. `EnableOrder == false` なら発注せず、接続確認とスプレッド計測のみ。
- `OnTick()`: kill switch の最小実装。当日（`Server.Time.Date` 基準）の実現+含み損益を集計し、`-MaxDailyLoss` を超えたら新規停止（フラグ）＋（既存保有があれば全決済）＋Print。
- `OnStop()`: 終了ログ。
- 注文・例外は握りつぶさない。失敗は理由を Print。

## 安全制約（厳守）
- デモ以外では絶対に発注しない（ハードガードで `Stop()`）。
- 既定（EnableOrder=false）では発注しない。ユーザーが true にした時だけ1回。
- live / 実弾口座には触れない。

## 成功基準
- 単一ファイルで、cTrader Automate にそのまま貼ってビルドが通る想定の、コンパイルしやすいコード（cAlgo API の慣用に厳密に従う）。
- デモガードが入っている。
- 発注・ログが明確で、READMEで誰でも入れられる。
- log.md に「ローカルC#コンパイラが無いためコンパイル検証は未実施」と明記。

## 制約
- 有料モデル禁止（Muse既定）。
- この端末に .NET SDK / csc が無いため、ローカルでC#コンパイルはできない。cAlgo API のメンバー名（`Account.AccountType`・`AccountType.Demo`・`Symbol.Spread`・`Symbol.PipSize`・`ExecuteMarketOrder`・`TradeResult.IsSuccessful`・`Stop()` 等）の綴りに最大限注意せよ。
- cTrader のバージョンは 5.1 と 5.6 が同居。両対応のため、安定した慣用のみ使う。

## 手順
1. plan.md 相当の設計メモを log.md に書く（最小・単一ファイル）。
2. GoldmineProbe.cs を実装。
3. README.md を書く（貼り方: cTrader → Automate → 新規cBot → 貼付 → Build → デモ口座のチャートにドラッグ → パラメータ設定 → 実行）。
4. 自己レビュー（cAlgo API の綴り・null 安全性・発注が1回だけか・デモガード）。
5. log.md を完成。git add + commit。

## 注意
- 発注ロジックは「1回だけ」。連続発注・ループ発注を書くな。
- GUIの実行はできない（cBotはcTrader内で動く）。此処ではコード生成と静的レビューまで。
