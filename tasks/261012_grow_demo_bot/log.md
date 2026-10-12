# log.md — 261012_grow_demo_bot

## やったこと
1. 既存cBot資産（Phronisis/GoldmineProbe、デモガード・kill switch・診断ログ）を土台に、戦略cBot `PhronisisTrend` を新規プロジェクトで作成。
2. `ctrader-cli create cbot PhronisisTrend csharp` でプロジェクト生成 → `PhronisisTrend.cs` を実装 → `ctrader-cli build` 成功（0エラー/0警告）。
3. `ctrader-cli run` のパラメータ渡し（`--<PropertyName>=<value>`）と、同一cTIDでの複数インスタンス同時接続を実機確認。
4. デモ（8066655）で EURUSD/USDJPY/GBPUSD h1 の3インスタンスを EnableTrading=true で起動。ログで起動確認。

## 検証結果
- build: success（errors空）
- 起動: 3/3 起動確認（`IsLive=False Asset=JPY Balance=103928 Equity=104070 EnableTrading=True`）
- 同一cTID×3接続: 成立（競合で落ちない）
- ログ: `Data\cBots\PhronisisTrend\<guid>-Default\RealTime\log.txt` に出力（Kaiが読める）

## 軌跡
| 論点 | 選んだ案 | 潰した案 | 理由 |
|---|---|---|---|
| 戦略 | Donchian20ブレイク+SMA200フィルタ両建て | マーチンゲール/グリッド | 破滅型はインチキ。正のスキューを狙う |
| サイジング | リスクベース（Equity×0.5%÷stopPips÷PipValue） | 固定ロット | 口座規模・ボラに非依存 |
| 複数ペア | 1インスタンス=1ペア | 1cBotで多シンボル | 実装の複雑さとバグリスク回避 |
| 実行 | ctrader-cli run（A） | 手動実行（B） | 根本さんの委任。デモ固定で安全 |
| 起動数 | 3ペアから | 全ペア一斉 | 様子見。過剰起動しない |

## 残課題（正直）
- OOS/フォワードエッジは未確認。数日〜数週の観察が必要。
- エグジットがSL/TPのみ（チャネル離脱・トレーリング未実装）。
- 起動プロセスの常駐管理（端末再起動で消える）。監視・再起動の仕組みは未整備。

<!-- status: complete | agent: kai -->
