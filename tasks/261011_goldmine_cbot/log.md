# log.md — 261011_goldmine_cbot

## plan相当の設計メモ（最小・単一ファイル）

- 方針: 単一ファイル GoldmineProbe.cs。OnStart=デモガード＋計測＋1回発注、OnTick=kill switchのみ、OnStop=終了ログ
- デモガードを先頭に固定し、非デモでは Stop して戻る
- 発注は OnStart のみ。_orderAttempted を Execute 前に立て、skip系全経路でも立て、OnTickでは発注しない
- 日次損は Equity差分（当日Equity - 当日起動時Equity、Server.Time.Dateで日替り検出）で近似。Positions/History集計はバージョン差があるため安定慣用を優先
- 例外は握りつぶさず Print。null（Account/Symbol/result/Position/Positions/Server）と PipSizeゼロ割をガード
- cTrader 5.1/5.6両対応のため安定慣用のみ: Account.*, Symbol.*, Server.Time, Positions, ClosePosition, ExecuteMarketOrder 6引数, TradeResult.IsSuccessful/Error/Position

## 軌跡表

| 論点 | 選んだ案 | 潰した案 | 理由 |
|------|----------|----------|------|
| 日次損の集計 | Equity差分（起動時Equity基準） | Positions+History合算 | History系APIの版差を避け5.1/5.6安定を優先、実現+含みの近似として十分 |
| 決済手段 | ClosePosition(position) | Position.Close() | Robot側メソッドの方が版を跨いで安定しPositions.ToList併用で列挙破壊を回避 |
| 発注回数担保 | _orderAttemptedをExecute前に立てる | 成功時のみ立てる | 例外時も再発注させないため先立てが安全、OnTick無発注と二重化 |
| Volume単位 | brief通りVolume素通し（lots想定0.01） | Units換算を挟む | brief指定の呼出し形を厳守、換算は版差と誤読の元になるため入れない |
| スプレッド超過時 | 見送り＋attempt済みにして終了 | 次Tickで再試行 | 連続発注の匂いを消し1回性を純化、確認用途は再実行で足りる |

招集判断: 6神なし。単一ファイル・依存1・仕様確定のため。Gaia不要（案分岐なし）、Hermes不要（既知の安定慣用のみ）、Artemis不要（3ファイル未満）、Daedalus不要（新規作成で既存バグなし）、Metis不要（レビュー観点は自己レビュー4点に集約）、Athena不要（統合対象なし）。

## 自己レビュー（静的）

- cAlgo API綴り: Account.AccountType / AccountType.Demo / Symbol.Spread / Symbol.PipSize / ExecuteMarketOrder / TradeResult.IsSuccessful / Stop を目視確認、他に Account.Number/BrokerName/Balance/Equity、Symbol.Name/Bid/Ask、Server.Time、Positions、ClosePosition、TradeType.Buy、Position.EntryPrice/SymbolName/Id、protected override OnStart/OnTick/OnStop を使用。安定慣用のみ
- null安全性: Account/Symbol/Server/result/result.Position/Positions を検査、PipSizeゼロ割をNaN回避、Positions.ToList()で列挙中変更を回避
- 発注1回: _orderAttemptedはOnStartでfalse初期化→全EnableOrder=true経路でtrue化→Execute前に立てる→OnTickに発注文なし。連続発注なし
- デモガード: OnStart先頭で AccountType!=Demo ならPrint+Stop+return。既定EnableOrder=falseで無発注
- ローカルC#コンパイラが無いためコンパイル検証は未実施。目視＋慣用照合のみ

## Hayatoゲート（4点）

1. 仕様逸脱: PASS。brief必須（単一ファイル/属性・名前空間/6パラメータ/デモガード/計測Print/1回発注+結果Print+スリッページ/EnableOrder=false無発注/OnTick kill switch/OnStop/失敗Print/README手順/log注記）を全て実装
2. バグ・セキュリティ致命傷: PASS。クラッシュ元はガード済み、権限はAccessRights.None、外部入出力なし、実弾ガードあり。ロジック誤り・性能の重欠陥なし
3. 手続き違反: PASS。brief/GoldmineProbe.cs/README.md/log.md 揃い、招集判断を記録、宣言と実体一致
4. 軌跡の品質: PASS。上表4列すべて非空

health check: python scripts/code_health_check.py --no-color → 5/5 PASS（ALL PASS）

判定: PASS（WARNなし）。自律確定可。

## 検証

- 静的レビューのみ実施（上記）
- ローカルC#コンパイラが無いためコンパイル検証は未実施
- cTrader側の確認は未実施（GUI実行不可の制約通り）。次段でデモチャートにて EnableOrder=false→true の順で確認する

## 残課題

- cTrader Automate実機でのBuild確認（5.1/5.6）
- デモでの EnableOrder=false probe確認、次に true で1回約定・ログ確認
- Volume単位の実機表示確認（lots想定の妥当性）
- 戦略ロジックは次段（本タスクでは入れない）

## Kai追記（コンパイル検証・2026-10-11）

- .NET SDK 6.0を導入し、cAlgo.API.dll（cTrader 5.6.9・net6.0）に対して `dotnet build` で型チェックした（`scratch/20261011_cbot_compilecheck/`）。
- 初回ビルドで CS0103 を検出: `AccountType.Demo` は存在しない。`cAlgo.API.Internals.AccountType` は Hedged/Netted（建玉方式）の enum であり、デモ/実弾の区別ではない。
- 修正: デモ/実弾判定を `Account.IsLive`（bool）に変更（`Account.IsLive==true` で ABORT→Stop）。startログにも IsLive を追加。
- 再ビルド: 0エラー / 0警告。コンパイル検証 PASS。

## Kai追記（実機フィードバック・BadVolume修正・2026-10-11）

- 実機（cTraderデモ・Account 8066655）で EnableOrder=true を実行 → `Executing Market Order to Buy 0.01 EURUSD` が `BadVolume` で失敗。
- 原因: cAlgo `ExecuteMarketOrder` の volume は units（通貨単位）であり lot ではない。0.01 を units として渡したため最小未満。
- 修正: `Symbol.QuantityToVolumeInUnits(Volume)` で lots→units に変換し、`Symbol.NormalizeVolumeInUnits(..., RoundingMode.ToNearest)` で正規化。`Symbol.VolumeInUnitsMin` 未満は SKIP。
- 併せて probe PASS を確認: IsLive=False（デモ）・Type=Hedged・spread 1.0pip 実測。
- 再ビルド: 0エラー。

## Kai追記（kill switch修正＋実機運用・2026-10-12）

- 実機（デモ 8066655）で発注成功直後、kill switch が `daily P/L -53 broke -MaxDailyLoss 50` で誤発火（開場3分）。0.01ロットの3分で-53は価格変動では説明できない。
- 原因の当て: `Max Daily Loss` を口座通貨の絶対額(50)で扱っており、口座規模・通貨に対して桁が合わない。
- 修正: `Max Daily Loss (%)`（起動時Equityに対する比率、既定1%）に変更（スケール非依存）。起動時に `Asset`/`Balance`/`Equity` と算出した限度額をPrint（-53の正体を次回確定する）。
- ビルド: 実プロジェクトを `ctrader-cli build "C:\Users\nemom\Documents\cAlgo\Sources\Robots\Phronisis"` でビルド成功（0エラー/0警告）。
- 運用確定: ソース実パスは `Documents\cAlgo\Sources\Robots\<名前>\<名前>\<名前>.cs`。Kaiが直接書き `ctrader-cli build` で確認、根本さんはcTraderで実行のみ（コピペ廃止）。手順 `knowledge/protocols/ctrader_cbot_workflow.md`（本家Core）。

## Kai追記（-53の正体確定・2026-10-12）

- cBotのログはファイルで残る（Kaiが読める）: `Documents\cAlgo\Data\cBots\<名前>\<instance-guid>-Default\RealTime\log.txt`。
- 実機ログで判明: 口座通貨は JPY（`Asset=JPY`）、Balance≈103,928 JPY。旧 `Max Daily Loss=50`（絶対額・円）は残高の約0.05%。EURUSD 0.01ロットで1pip≒15円なので、3pip逆行で -45〜-53円 → 誤発火していた。物理的異常ではなく、限度額の桁ミス。
- 修正後（1%＝1,040 JPY）: 誤発火なし。発注成功（Buy EURUSD 0.01 lots=1000 units、Entry=1.12115、slippage 0）、稼働中。
- 教訓: 損切りラインは絶対額でなく残高比率で持つ（通貨・口座規模に非依存）。

<!-- status: complete | agent: kai -->

