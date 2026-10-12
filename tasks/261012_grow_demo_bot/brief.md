# タスク: 261012_grow_demo_bot — デモ口座を増やすボット（PhronisisTrend）

## 目的
Axioryデモ口座（8066655, JPY, 約103,928）を増やすボットを、デモ範囲で試す。
目標（10万→50万=5倍）は努力目標であり保証しない。破滅型（マーチンゲール/グリッド）は使わない。リスク管理を土台にする。

## 成果物
- `PhronisisTrend.cs`（cBot本体。Donchianブレイク＋長期SMAフィルタ、ATRストップ、リスクベースのロット、日次損失halt、デモ限定ガード、全ログ）
- `PhronisisTrend.csproj`（cTrader Automateプロジェクト）
- 運用: `ctrader-cli run` で起動（1インスタンス=1ペア）

## 起動（A: Kai側から）
```
ctrader-cli run "<...>\PhronisisTrend.algo" `
  --ctid=makanaosans@gmail.com --pwd-file="C:\Users\nemom\Desktop\ctpass.txt" `
  --account=8066655 --symbol=EURUSD --period=h1 --EnableTrading=true
```
- パラメータは `--<PropertyName>=<value>` で渡す（例 `--RiskPerTradePct=1.0`）。未指定は既定。
- 既定: RiskPerTradePct=0.5, DailyLossPct=2.0, MaxPositions=1, EntryPeriod=20, TrendSmaPeriod=200, AtrPeriod=14, AtrStopMult=2.0, RewardRisk=2.0, EnableTrading=false
- 安全: `--account=8066655`（デモ、Live=false）固定。実弾 `9018428` には絶対に向けない。cBot側にもデモガードあり。

## 起動中（2026-10-12〜）
- EURUSD h1 / USDJPY h1 / GBPUSD h1 の3インスタンス（EnableTrading=true）
- 停止: `Get-Process ctrader-cli | Stop-Process`（全停止）
- ログ: `Documents\cAlgo\Data\cBots\PhronisisTrend\<guid>-Default\RealTime\log.txt`

## ロジック（v1）
- OnBar（確定足）で判定。シグナル足は `Bars.Count-2`（確定済み）。
- エントリ: 直近 EntryPeriod 本の高値/安値（当該足を除く）をブレイクし、かつ終値が SMA(TrendSmaPeriod) の正しい側 → Buy/Sell。既存ポジションなしの時のみ。
- SL = AtrStopMult × ATR（pips換算）、TP = RewardRisk × SL。
- ロット = Equity × RiskPerTradePct% ÷ (stopPips × Symbol.PipValue)。正規化し最小未満は見送り。
- 日次: 起動時Equityを基準に下落が DailyLossPct% 超 → 全決済＋当日停止。
- デモ以外は OnStart で ABORT→Stop。

## 未検証・残（正直）
- バックテスト検証は本構成では未（前プローブの素朴トレンドはOOSエッジなし）。当面はフォワード観察が主。
- ペア数・時間軸・パラメータ・エグジット（チャネル離脱）は要調整。
- 5倍は努力目標。負ける可能性を前提に、リスク上限で守る。
