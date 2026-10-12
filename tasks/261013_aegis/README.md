# Aegis（根本さんの既存cBot）— 参考コード

根本さんの別端末で開発された cBot。根本さん評価「ある程度筋の良い失敗作」。フロニシスのbotプロジェクトの参考コードとして保全。

- ソース: `Aegis_13_RsiFalling_RetestOnly_v1_validationexit-1.cs`（92.8KB, 144パラメータ）
- 入手: gdrive `toKaiFiles` から rclone で取得（2026-10-13）。Driveリンクは認証が必要で直接DL不可だった。
- 種別: Sell-only「レンジ・リテスト」戦略（EURUSD M10想定）。
  - HTFスイング高値（H4）のレジスタンス、RollingHigh(H1)、EMAリテストのレベル。
  - エントリ: レベルへのリテスト＋ベア足確認、RSI品質ゲート（6層）、RSI弱再攻撃フィルタ、ACD（Anti-Chop Detector, 7分足×15本レンジ）。
  - Exit: 3層（利益コア: 固定TP/RSIリターン/トレーリング、無効化コア、早期損傷コア: EarlyDeny/Expiry/NoProfit/SpeedCut等）。
  - JSTセッション、Optimizationモード（OPT:* パラメータ切替）。
- ビルド: cTrader 5.10 で build 成功（obsolete警告1のみ）。
- 初期バックテスト: EURUSD m10 1ヶ月 → Net +612 / PF 3.02 / **3取引のみ**（超選択的。統計的に無意味）。
- 持ち込み先: `Documents\cAlgo\Sources\Robots\AegisRR\`（プロジェクト名 AegisRR）。

## 拾える設計（他botに反映）
- 早期損傷カット（N本で含みが伸びなければ撤退）
- Anti-Chop（レンジ回避）
- RSI品質ゲート（多層）
- レベル基準エントリー（HTFスイング/EMA）

## 注意
- 144パラメータ＝過剰最適化リスク大。そのまま真似ず思想を借りる。
