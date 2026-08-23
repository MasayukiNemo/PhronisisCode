# plan.md — ステートセーブ 実装計画

## アーキテクチャ

```
docs/tetris/index.html（単一HTML、1013行→~1150行目安）
├── <style> : 既存 + .save-flash / SAVEインジケータ（.save-indicator）、SAVED/NO SAVE等のフラッシュ用クラス
├── DOM: .side に SAVE/LOADボタン追加（#btnSave #btnLoad）、CONTROLSに S/L 行追加、フラッシュ用 #saveFlash 要素
└── <script> IIFE 追加:
    ├── 定数: SAVE_KEY='phronisis_tetris_save_v1', SAVE_VERSION=1
    ├── 関数: serializeState() -> JSON、deserializeState(json) -> state適用、doSave()、doLoad()、showSaveFlash(msg)
    ├── 状態保存対象: board(20x10 deep copy), current{type,matrix,pos,rot,color}, nextQueue[3], holdType, holdLocked, bag, score, level, lines, lockTime, lockResets, lastRotated, dropCounter, isStarted, isGameOver, isPaused, 保存時刻 savedAt
    ├── ロード時: JSON.parse try/catch → バリデーション（board配列/ current type等）→ 復元 → dropCounter=0, lockTime=0, lastTime=performance.now(), hideOverlay, isStarted=true, isPaused=false, updateUI/draw
    ├── S: プレイ中のみ doSave()、L: 常時 doLoad()。try/catchで quota exceeded / 無効時は SAVE FAILED / CORRUPTED を表示
    └── 入力: KeyS / KeyL をハンドラに追加（preventDefault不要、e.repeat無視）、ボタンは click で doSave/doLoad
```

- 保存はプレイ中のみ、ロードは常時。Sの誤爆でタイトル時の保存は弾く
- 上書きは1スロット、ロードは冪等。破損時は「CORRUPTED」を表示しクラッシュしない

## 招集判断

| 知性体 | 招集 | 理由 |
|--------|------|------|
| Gaia | しない | 設計は保存先/範囲/キーで収束、発散不要 |
| Hermes | しない | localStorageは既知API、事実確認不要 |
| Artemis | しない（Kaiが本planで代替） | 変更ファイル1つ、依存0 |
| Daedalus | する | 実装・バグ検出: localStorage直列化/復元の現実化、file://制限時のフォールバックを委任 |
| Metis | する | 実装を伴うため原則招集。1150行の可読性レビューを委任 |
| Athena | しない | 2体逐次をKai統合 |

→ 逐次: Daedalus → Metis

## タスク分解

1. [x] T1: Daedalus — localStorage直列化/復元コア（serialize/deserialize/doSave/doLoad/showFlash）とキー/ボタン配線の実装
2. [x] T2: Daedalus — UI追加（SAVE/LOADボタン、CONTROLS行、フラッシュ要素、インジケータ）とスタイル調整
3. [x] T3: Metisレビュー + Kai統合修正
4. [x] T4: 自己検証（7必須の手動+S/L操作 + 永続性F5テスト + code_health 5/5 PASS）

## 依存関係

```
T1 → T2 → T3 → T4
```

## リスク

- リスク1: localStorage無効/容量超過 → 対策: try/catchで SAVE FAILED を表示、クラッシュさせない
- リスク2: 破損JSONでクラッシュ → 対策: parse try/catchで CORRUPTED を表示、復元を中断
- リスク3: ロード時の時間系暴走 → 対策: dropCounter/lockTime/lastTimeを0/nowへリセットしてから再開
- リスク4: 行数1150超過 → 対策: セクション分離、保存ロジックは1ブロックに集約
- リスク5: S/Lと既存キー競合 → 対策: S/Lは単押しのみでCtrl+Sとは衝突しないことをbriefで明記、preventDefault不要

