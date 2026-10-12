# Aegis系 過去作から拾う種（2026-10-13）

根本さんの2026年2〜3月の試行群（`variants/` に保全）。失敗作が多いが、リビルドの種がある。

## 各本の手法
- `AegisAtrEnvironment_cTrader.cs`（指標）: ATR と ATR移動平均の比＋傾きで局面を判定。**Expansion**（比≥1.15＆上昇）/ **Compression**（比≤0.90＆下降）/ Neutral。
- `Aegis_Sniper_v6_AdxDynamic_...BUILD.cs`: **ADXで動的適応**。`WaveMode=FixedPips|AtrMultiplier`、`TradeDir=SellOnly|BuyOnly|Both|Auto`、SemiAuto/FullAuto、Throttled（過剰取引抑制）、AutoDecisionLog。
- `Aegis_Breakout_Core_v1_09a.cs`: ブレイクダウン→リテスト型（HTF H4 バイアス＋LTFリテスト）。環境ガード（session/spread/cooldown/ACD/ATR）。
- `Aegis_RR_S7_ACD_RollingHigh_FIXED.cs`: レンジ・リテスト。**ACD（Anti-Chop Detector）＝HTFレンジが [MinRange..MaxRange] 内のときだけ取引**。RSI品質ゲート、部分決済＋トレーリング、JSTセッション。「skip when unsure / skim tasty parts」＝選択性が設計目的。
- `Aegis_PFF_v2_2_DualMode.cs` / `Aegis_PFF_v2_3_DelayedEntry.cs`: DualMode（二重モード）、DelayedEntry（エントリー遅延）。MinBarsBetweenEntries、OnePositionMax、entry arrows描画。

## 拾う種（リビルドの芯）
1. **選択性の正体＝ACD（HTFレンジの上下限フィルタ）＋品質ゲート。** これが「黙る」機構。型だけ真似て外すと即死（PhronisisAegis v1 = 822取引 -48%）。
2. **局面適応の正体＝ATR環境（Expansion/Compression）＋ADX。** 閾値のATR比化だけでなく、局面判定でオン/オフ＋パラメータ切替をする。＝根本さんの「局面ごとにパラメータ調整」の自動化。
3. **AtrMultiplier モード**（pipsでなくATR倍率で閾値を持つ）＝レジーム非依存。
4. **Throttled（過剰取引抑制）／MinBarsBetweenEntries／OnePositionMax**＝切磋の抑制装置。
5. バリアント: ブレイクダウン・リテスト、DelayedEntry、DualMode（fade と breakout の両対応）。

## 含意
- リビルド方針: Aegisの「型×選択性」を、ATR環境＋ADXで局面適応させ、ACD的なレンジフィルタで黙らせる。取引数はAegis原版（53/年）寄りに保ちつつ、局面でパラメータを切り替える。
- PhronisisAegis v1（ATR比化のみ・選択性欠如）は失敗。次版はACD＋ATR環境を必ず入れる。
