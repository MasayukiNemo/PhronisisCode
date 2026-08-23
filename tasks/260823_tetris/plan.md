# plan.md — 実装計画

## アーキテクチャ

```
docs/tetris/index.html（単一HTML）
├── <style> : レイアウト（フィールド+サイドバー）、ダーク基調、Canvas枠、操作説明
├── <canvas id="board"> 300x600 (10x20 * 30px) + <canvas id="next"> 4x4 preview
└── <script> (IIFE + 'use strict', 非moduleで file:// 対応):
    ├── 定数: COLS=10, ROWS=20, BLOCK=30, 7テトロミノ定義（4x4行列+色）、速度テーブル
    ├── 状態: board[20][10], current {type, matrix, pos}, next, score, level, lines, dropTimer, isPaused, isGameOver
    ├── コア: createMatrix(type), rotate(matrix), isValid(board, matrix, pos), merge, clearLines, getGhostPos, spawn
    ├── 入力: keydown（ArrowLeft/Right/Down/Up, Space, KeyR, KeyP）— preventDefaultでスクロール抑止
    ├── ループ: requestAnimationFrame + deltaTime で落下（level速度）、接地即固定（lockDelayなし）、スポーン衝突でゲームオーバー
    └── 描画: drawBoard, drawCurrent, drawGhost(alpha 0.28), drawNext, drawUI
```

- 技術選定: Canvas 2Dのみ。音声・外部フォント・ライブラリ不使用で file:// でも動作保証
- トレードオフ: 単一HTMLは可読性で分割に劣るが、配布・実行容易性を優先。JSは IIFE + strict でスコープ分離

## 招集判断

| 知性体 | 招集 | 理由 |
|--------|------|------|
| Gaia | しない | 設計2案は deep_thought と brief 軌跡で収束済み。追加の発散不要 |
| Hermes | しない | 未知ライブラリ/外部API調査不要（Vanilla Canvas） |
| Artemis | しない（Kaiが本planで代替） | 変更ファイル1つ、依存0で閾値未満。planの責務は本ファイルで担保し軌跡に記録 |
| Daedalus | する | 実装・バグ検出の専門性が必要。Canvas描画・当たり判定・回転の現実化を委任 |
| Metis | する | 実装を伴うタスクは原則招集。可読性・保守性のレビューを委任 |
| Athena | しない | 統合対象は Daedalus→Metis の逐次2体のみで Kai が統合可能 |

→ 逐次委任: Daedalus（実装）→ Metis（レビュー）→ Kai統合

## タスク分解

1. [ ] T1: `docs/tetris/index.html` 骨格作成（Canvas配置、スタイル、UI領域、操作説明）
2. [ ] T2: テトロミノ定義・ボード管理・衝突判定・回転（壁キック簡易2パターン）実装
3. [ ] T3: 落下ループ・固定・ライン消去・スコア/レベル・スポーン・ゲームオーバー実装
4. [ ] T4: ゴースト表示・NEXT描画・ハードドロップ・ソフトドロップ・入力ハンドリング
5. [ ] T5: ポーズ/リスタート、UI表示、微調整（色・フォント・レスポンシブ）
6. [ ] T6: 自己検証（手動プレイ + code_health_check）

## 依存関係

```
T1 → T2 → T3 → T4 → T5 → T6
```

## リスク

- リスク1: キー入力でページスクロールが発生 → 対策: keydown で Arrow/Space の preventDefault
- リスク2: file:// で Canvas taint やモジュールCORS → 対策: type="module" 不使用、単一HTML内 script（非モジュール）で回避
- リスク3: 回転時の壁突き抜け → 対策: isValid で全セル検証、壁キック2パターンで救済
- リスク4: 無限ループや高速落下での固定漏れ → 対策: 接地即固定とし、スポーン衝突でゲームオーバーを明確化（lockDelayは複雑化のため見送り）

