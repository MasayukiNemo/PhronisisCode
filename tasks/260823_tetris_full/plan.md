# plan.md — ガイドライン拡張 実装計画

## アーキテクチャ

```
docs/tetris/index.html（単一HTML拡張、900-1100行目安）
├── <style> : 既存維持 + HOLD/NEXT拡張、HOLD 80x80 / NEXT 96x200 縦3段
├── <canvas id="board"> 300x600 (10x20*30) + <canvas id="hold"> 80x80 + <canvas id="next"> 96x200
└── <script> IIFE:
    ├── 定数: COLS/ROWS/BLOCK, COLORS/SHAPES, SRS_KICKS_JLSTZ / SRS_KICKS_I (8状態×5試行), T-Spin判定用
    ├── 状態: board, current {type,matrix,pos,rot}, holdType, holdLocked, nextQueue[3], bag, score/level/lines, dropTimer, lockDelayTimer/lockResets, dasState, isPaused/isGameOver/isStarted
    ├── コア: createPiece, rotateCW/CCW, applySRS(kickTable, fromRot, toRot), isValid, merge, clearLines(with T-Spin), getGhostPos, spawn(with ARE), hold()
    ├── 入力: keydown/keyup（ArrowLeft/Right/Down/Up, X, Z, Space, KeyC, KeyP/KeyR）— preventDefault拡張、DAS/ARR用 interval管理
    ├── ループ: requestAnimationFrame + delta, 接地検出→lockDelay 500ms/15回、are直後spawn、DAS(150)→ARR(30)で連続move
    └── 描画: drawBoard/drawHold/drawNext3/drawGhost/drawCurrent/drawUI + T-Spin演出
```

- 技術選定: 既存 IIFE/Canvas維持。テーブル駆動でSRS複雑さをデータに閉じ込める
- 行数対策: セクション見出し（// ---- SRS ---- 等）と関数分離で可読性担保

## 招集判断

| 知性体 | 招集 | 理由 |
|--------|------|------|
| Gaia | しない | 設計は「フルSRSを足す」で収束、発散不要 |
| Hermes | する | SRS kick table の事実確認（Tetris Wiki準拠の8状態×5試行）が専門的検証を要する |
| Artemis | しない（Kaiが本planで代替） | 変更ファイル1つ、依存0。Hermesの調査結果をKaiが統合すれば十分 |
| Daedalus | する | 実装・バグ検出の核。ロックディレイ/DAS/T-Spinの現実化を委任 |
| Metis | する | 実装を伴うため原則招集。900行超の可読性レビューを委任 |
| Athena | しない | 3体（Hermes→Daedalus→Metis）の逐次をKaiが統合 |

→ 逐次: Hermes（仕様確認）→ Daedalus（実装）→ Metis（レビュー）

## タスク分解

1. [x] T1: Hermes — SRS kick table の事実確認と brief定義との突合（JLSTZ/I/Oの8状態×5試行をコード値として確定）
2. [x] T2: Daedalus — SRS両回転 + 壁キック適用、ホールド（C）、NEXT3、HOLD表示の骨格実装
3. [x] T3: Daedalus — ロックディレイ500ms/15回、DAS150/ARR30、T-Spin判定・スコア補正の実装
4. [x] T4: Daedalus — 入力体系統合（↑/X CW、Z CCW、Space Hard、Hold、Pause/Restart）とUIキー説明更新、ghost/描画調整
5. [x] T5: Metisレビュー + Kai統合修正（未使用drawMini削除）
6. [x] T6: 自己検証（リグレッション8点 + 新規8点 + code_health 5/5 PASS）

## 依存関係

```
T1(Hermes) → T2 → T3 → T4 → T5(Metis) → T6
```

## リスク

- リスク1: 行数肥大で単一HTMLが1100行超過 → 対策: 上限監視、セクション分離、テーブルは定数ブロックに集約
- リスク2: ロックディレイ無限粘り → 対策: 15回上限 + 最終リセットから500msで強制固定
- リスク3: Shift衝突 → 対策: HoldはCのみに限定（briefで決定）、Shiftは受け付けない
- リスク4: DAS誤発火で移動過多 → 対策: keyupでタイマークリア、DAS 150/ARR 30を定数化して調整可能に
- リスク5: T-Spin誤検出 → 対策: 3コーナー法（Tミノの4角中3角が埋まっている + 回転が直前の操作）で簡易判定に留める

