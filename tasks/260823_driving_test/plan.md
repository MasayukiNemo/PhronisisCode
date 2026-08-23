# plan.md — 駆動試験 実行計画（Kai が埋める）

## アーキテクチャ

（Kai が設計を記述）

## タスク分解

1. [ ] Hermes: 既存ファイル構造の調査
2. [ ] Gaia: チェック設計（5検査の入出力定義）
3. [ ] Artemis: 実装計画・依存関係整理（見積・クリティカルパス3行を含む）
4. [ ] Daedalus: scripts/code_health_check.py 実装
5. [ ] Metis: 品質レビュー（可読性・保守性）
6. [ ] Athena: 5検査の統合と CLI 出力整形

## 依存関係

```
Hermes → Gaia → Artemis → Daedalus → Metis → Athena
```

## リスク

- リスク: 既存 hooks との整合性崩し → 対策: 既存ファイルを直接編集しない
