# plan.md — T変換パワー 実装計画

## アーキテクチャ

```
docs/tetris/index.html（1286行→~1350行目安）
├── <style> : 既存 + T-POWERゲージ（3マス、#a855f7発光、消費演出） + +1/+2ポップ用 .power-pop
├── DOM: SIDEのHOLD下に T-POWERカード（#powerGauge 3マス + #powerText 0/3）追加、#powerPop 要素（中央やや上）
└── <script> IIFE 拡張:
    ├── 定数: POWER_MAX=3, T_COLOR='#a855f7', isPowerConversion フラグ
    ├── 状態: powerStock 0..3, isPowerConversion bool, powerPopTimer
    ├── 蓄積: clearLines内で cleared===3?1: cleared===4?2:0 を算出、isPowerConversionなら加算スキップ、powerStock = min(POWER_MAX, +add)、add>0かつoverflowなしで showPowerGain(+1/+2)
    ├── 変換: function tryConvertToT() — powerStock>=1 && current.type!=='T' && !isCountdown/isPaused/isGameOver && isValidでT行列生成（SHAPES.Tをrot回rotate）、SRS_JLSTZでkick試行、成功時のみ powerStock--、currentをTに置換（color T, rot維持）、isPowerConversion=true、lockTime/lockResetsをリセット経由で処理、失敗は無消費で揺れ演出
    ├── ゲージUI: updatePowerGauge() — 3マスにfilledクラス、満タンでpulse、消費でshrink
    ├── 保存: serializeState/isValidSaveData/doLoad/doLoadAuto/reset/spawnNext にpowerStockを含め、旧セーブ欠損は0で初期化
    └── 入力: KeyG/KeyW 両対応（e.ctrl/meta/alt除外、e.repeat無視）、HOLD Cとは別、カウント中は無効
```

- ループ断ち: 変換で生まれたTが含まれるロックでは一切加算しない（フラグで制御、次ロックで解除）
- 失敗時無消費: SRS全 kick失敗なら powerStock触らず、短い揺れのみ

## 招集判断

| 知性体 | 招集 | 理由 |
|--------|------|------|
| Gaia | 済（並列議論） | 3案の設計比較を提示 |
| Hermes | しない | 既知APIのみ |
| Artemis | 済（並列議論） | WBSとクリティカルパスを提示 |
| Daedalus | する | 実装・バグ検出: 変換のSRS流用とロック延長の現実化を委任 |
| Metis | 済（並列議論） | 3マスvsバーの品質判断を提示 |
| Athena | 済（統合） | 上限3・溢れ消失・フラグ断ちで統合 |

→ 残り逐次: Daedalus（実装）→ Metis（レビュー軽量）→ Hayatoゲート

## タスク分解

1. [x] T1: Daedalus — 状態追加（powerStock/isPowerConversion）、蓄積ロジック（clearLines加算+溢れ消失）、変換実行（G/W+SRS）、ゲージUI（3マス+演出）
2. [x] T2: Daedalus — セーブ/ロード拡張（powerStock保存・旧互換）、入力配線（G/W）、リグレッション担保
3. [x] T3: Metis軽量レビュー + Kai統合（filler削除）
4. [x] T4: 自己検証（6必須の手動確認 + code_health 5/5 PASS）

## 依存関係

```
T1 → T2 → T3 → T4
```

## リスク

- リスク1: 無限ループ — 対策: isPowerConversionフラグで変換由来消去は加算スキップ
- リスク2: 壁キック失敗でパワー消失 — 対策: 成功時のみ消費、失敗は揺れのみ
- リスク3: 行数1400超過 — 対策: ゲージはdiv3つ+CSS、T行列生成はrotateMatrix再利用
- リスク4: ゲージ視認性 — 対策: 3マスは# a855f7、満タンでpulse、消費でshrink、+1/+2ポップはT-SPIN流用
- リスク5: セーブ互換 — 対策: isValidSaveDataで0<=powerStock<=3を検証、欠損は0初期化、vは上げない

