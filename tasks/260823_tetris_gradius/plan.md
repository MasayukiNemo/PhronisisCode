# plan.md — グラディウス式武装 実装計画

## アーキテクチャ

```
docs/tetris/index.html（1149行→~1280行目安）
├── <style> : 既存 + T-POWERゲージ3マス（.power-cell） + ストックTアイコン（#tStockIcon、武装時発光） + BURST赤点滅 + #countdown
├── DOM: SIDEに T-POWERカードを刷新（ゲージ3マス + ストックTアイコン + ARMED/BURSTテキスト）、SIDEは3列維持
└── <script> IIFE 拡張（既存T-POWER直接変換を置換）:
    ├── 定数: POWER_MAX=3, ARM_COOLDOWN=300, CONVERT_COOLDOWN=200, T_COLOR
    ├── 状態: powerGauge 0..3, tStock 0/1, isPowerConversion, armLockUntil, convertLockUntil, burstTimer
    ├── 蓄積: clearLinesで cleared 3→1/4→2/他0を算出。powerGauge===3なら burst（gauge=0、showBurst()、stockは保持）してreturn。そうでなければ gauge = min(3, gauge+add)、2→3はどちらのaddでも3へ（クリップで自然に実現）
    ├── 武装: tryArm() — gauge===3 && stock===0 && now>=armLockUntil && !isCountdown... の時に stock=1、gauge=0、armLockUntil=now+300、演出（ゲージ消灯→ストック点灯）
    ├── 発射: tryConvertToT() — stock===1 && now>=convertLockUntil && current.type!=='T' の時にT行列生成→SRS kick、成功時のみ stock=0、currentをTに置換、isPowerConversion=true、lockリセット、失敗時は convertLockUntil=now+200 + 揺れで無消費
    ├── 入力: G/W両対応を1ハンドラ tryTPower() に統合。gauge===3 && stock===0 なら武装、stock===1 なら発射、どちらでもなければ無視。e.repeat無視、isCountdown等でガード
    ├── ゲージUI: updatePowerGauge() — 3マスのfilled、stockアイコンのarmedクラス、BURST時はgauge赤点滅1秒
    └── 保存: serializeState/isValidSaveData/doLoad/doLoadAuto/reset に powerGauge/tStock を含め、旧欠損は0初期化、burst状態は保存不要
```

- 同一キーG/Wの2回押しはarmLockで誤爆防止、変換失敗は200msクールダウンで無限試行を防ぐ
- ストック中の再蓄積は gaugeが0から再びたまるため、最硬防御（stock1+gauge3）が1-2ラインで維持可能

## 招集判断

| 知性体 | 招集 | 理由 |
|--------|------|------|
| Gaia | しない（Hayatoで再設計済み） | 設計は2段階で収束 |
| Hermes | しない | 既知APIのみ |
| Artemis | しない（Kaiが本planで代替） | 1ファイル変更 |
| Daedalus | する | 実装・バグ検出: 同一キー誤爆とバースト条件の現実化を委任 |
| Metis | する | 実装を伴うため原則招集。ゲージ/ストックの視認性レビューを委任 |
| Athena | しない | 2体逐次をKai統合 |

→ 逐次: Daedalus → Metis

## タスク分解

1. [x] T1: Daedalus — 状態2変数化（powerGauge/tStock）、蓄積（3で1/4で2、2→3クリップ、バースト）、武装/発射の同一キー分離（300ms/200msロック）、SRS変換のSRS流用
2. [x] T2: Daedalus — ゲージUI刷新（3マス+ストックTアイコン+ BURST赤点滅）、セーブ/ロード拡張（gauge/stock保存）、入力統合（G/W）
3. [x] T3: Metisレビュー + Kai統合
4. [x] T4: 自己検証（8必須の手動確認 + code_health）

## 依存関係

```
T1 → T2 → T3 → T4
```

## リスク

- リスク1: 同一キー誤爆 → 対策: 武装後300msロック、失敗時200msクールダウン、UIでARMED/FIRE READYを色で区別
- リスク2: ストックとゲージの二重管理で認知崩壊 → 対策: 3マスは横並び紫、ストックはTアイコンで縦分離し発光色を金に分離
- リスク3: バースト条件の抜け → 対策: gauge===3でstock有無に関わらず3/4消しでBURST、gaugeのみ0に戻しstockは保持
- リスク4: 変換失敗で無限試行 → 対策: 失敗は無消費だが200msロック+揺れで連打を抑制
- リスク5: 行数1300超過 → 対策: ゲージはdiv3つ+CSS、ロジックはtryArm/tryConvertに集約

