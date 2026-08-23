# 引き継ぎ書 — PhronisisCode

## この文書の性質

本ファイルは PhronisisCode の運用要約と引き継ぎを担う。
PhronisisCore の handover.md から分岐した軽量版であり、独立して進化する。

## 構成

```
.opencode/rules/phronisis_code.md  # 憲章 v1.0
opencode.json                       # 6神プール+hayato+yuna（プール。常時全起動しない）
shared/phronisis_code/              # 本体（orchestration_flow_code.md + agents/ + protocol/）
knowledge/                          # 軽量知識ベース（handover.md / conductor_profile_lite.md / decisions/ / session_log/ / code_knowledge/）
tasks/                              # タスクワークスペース（_template/brief.md plan.md log.md + deep_thought.md は実行時に生成）
hooks/                              # pre-commit/pre-push + python_run.sh/utf8_check.py/handover_check.py
```

## 環境定義

| ホスト名 | 環境 | 備考 |
|---------|------|------|
| DESKTOP-QCLBNKI | 開発拠点 | 初期構築端末 |

## セッションログ（要約）

| 日付 | トピック | 要約 |
|------|---------|------|
| 2026-08-23 | PhronisisCode創設 | PhronisisCoreから分岐。6神プール/L2.5維持/Hayatoゲート4点チェック/再アンカー機構を設計。Hayatoレビューで9本の刺しを検出し6点の補正を実施。独立進化方針で確定。 |

## 残課題

- 初回タスクでの実戦検証
- 本家からの有益な改善の手動取り込みルールの運用確認
