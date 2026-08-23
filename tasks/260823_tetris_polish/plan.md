# plan.md — オートセーブ + 321カウントダウン 実装計画

## アーキテクチャ

```
docs/tetris/index.html（1116行→~1250行目安）
├── <style> : 既存 + #countdown（48px中央、カウント用） + .save-flash.auto（水色） + トランジション調整
├── DOM: 既存 SAVE/LOADカード維持、#countdown 要素追加（.board-area 内、絶対配置）
└── <script> IIFE 追加/拡張:
    ├── 定数: SAVE_KEY='phronisis_tetris_save_v1', AUTO_SAVE_KEY='phronisis_tetris_auto_v1', SAVE_VERSION, COUNTDOWN_MS=600, AUTO_SAVE_LINES=10
    ├── 状態: isCountdown, countdownTimer, autoSaveLastLines, saveFlashQueue
    ├── オートセーブ: function tryAutoSave() — clearLines後にlinesが10で割り切れかつautoSaveLastLines!==lines の時のみ、直列化→AUTO_SAVE_KEYに保存→showSaveFlash('AUTO SAVED', true)（水色、カウント中は抑制）
    ├── カウントダウン: function startCountdown(onDone) — isCountdown=true、clearDAS/stopSoftDrop、入力無効、3→2→1を600ms間隔で #countdown に表示、終了時に isCountdown=false、lastTime=performance.now(), lockTime=0, dropCounter=0 で再開、フラッシュキューがあれば表示
    ├── 統合: doLoad() は復元後に needsCountdown=trueで startCountdownを呼ぶ（盤面は即描画しつつ操作はカウント後に解放）。reset() と togglePause()（Lv>=3時）も同様に startCountdownを挟む。カウント中は loop() と keydown の先頭で isCountdown ガード
    └── 保存/復元: serializeStateは共通、isValidSaveDataは両キーで共用、updateSaveIndicatorは両キーの存在を表示（● SAVED hh:mm + ● AUTO hh:mm）
```

- 手動と自動は別キーで保護。Lは手動優先、手動がなければAUTOをフォールバック、ボタンLOADも同様
- カウント中は重力/DAS/ロック/ソフトドロップ/入力すべて停止し、終了時にタイマーリセット

## 招集判断

| 知性体 | 招集 | 理由 |
|--------|------|------|
| Gaia | しない | 設計は2機能追加で収束 |
| Hermes | しない | 既知APIのみ |
| Artemis | しない（Kaiが本planで代替） | 変更1ファイル、依存0 |
| Daedalus | する | 実装・バグ検出: カウント中の完全停止とオートセーブの分離を現実化 |
| Metis | する | 実装を伴うため原則招集。1250行の可読性レビュー |
| Athena | しない | 2体逐次をKai統合 |

→ 逐次: Daedalus → Metis

## タスク分解

1. [x] T1: Daedalus — オートセーブコア（別キー、10ライン毎、カウント中抑制、AUTO SAVEDフラッシュ）と手動保護の実装
2. [x] T2: Daedalus — 321カウントダウン（#countdown要素、isCountdownフラグ、完全停止/再開、LOAD/R/ポーズ解除分岐）の実装
3. [x] T3: Metisレビュー + Kai統合修正
4. [x] T4: 自己検証（6必須の手動/オート/カウント + 永続F5 + code_health 5/5 PASS）

## 依存関係

```
T1 → T2 → T3 → T4
```

## リスク

- リスク1: オートセーブが手動を潰す → 対策: 別キー `auto_v1` で分離、Lは手動優先フォールバック
- リスク2: カウント中のタイマー暴走 → 対策: isCountdownで重力/lock/DAS/softDrop/入力すべて停止、終了時にlastTime/lockTimeリセット
- リスク3: フラッシュ同時表示 → 対策: カウント中はAUTO SAVEDをキューし、カウント終了後に表示
- リスク4: 行数1300超過 → 対策: セクション分離、カウントとセーブのロジックを各1ブロックに集約
- リスク5: ポーズ解除のLv判定チラつき → 対策: 解除時点のlevelを一度だけ評価し、分岐を確定させる

