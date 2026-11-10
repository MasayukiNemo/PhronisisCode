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
| BUF-STMarketingnoMacBook-Air.local | Mac (macOS Tahoe / arm64) | homebrew 5.1.11, python 3.12.14, git 2.54.0, gh 2.98.0, opencode-desktop 1.18.25, Code 検証済み (5/5 PASS) |
| PC122-00290 | Windows 11 Pro 24H2 / 会社PC | python 3.13.5, git 2.54.0.windows.1, rclone 1.74.1, node 22.17.0, OpenCode.exe 1.18.25, PhronisisCore 併存, Code 検証済み (5/5 PASS 2026-09-01), gh未導入（git credentialでpush可）, hooks=bash via Git for Windows |
| LAPTOP-VO3C74SH | Windows 11 Home 26300 / 個人端末（常時稼働・RDPホスト） | python 3.11.1, git 2.54.0.windows.1, node 24.15.0, opencode 1.18.34, agy, playwright, crawl4ai, rclone 1.74.0. 会社端末ではない（本家PhronisisCore側handoverに環境詳細あり） |

## セッションログ（要約）

| 日付 | トピック | 要約 |
|------|---------|------|
| 2026-08-23 | PhronisisCode創設 | PhronisisCoreから分岐。6神プール/L2.5維持/Hayatoゲート4点チェック/再アンカー機構を設計。Hayatoレビュー9本→6点補正、深層思考で軽さは判断回数と検証。独立進化方針で確定。 |
| 2026-08-23 | 大規模レビュー+修正 | 6視点レビュー（Gaia/Hermes/Daedalus/Metis/Yuna/Hayato）でP0 3点（パス/ hooks/ 6神profile）を検出。深層思考でfast-pathとdrift自動化を見送り7点に絞って修正。Hayato二巡目で残BLOCK（utf8_check/テンプレート残骸）を検出し再修正。 |
| 2026-10-06 | Orca駆動版（Orca導線＋クイズ リッチWeb UI版） | `docs/orca/README.md`（任意のOrca導線）＋AGENTS.mdに1行導線。実タスク=クイズのリッチWeb UI版をworker（opencode）がフルフロー＋Hayatoゲートで完走（flow_test 36/36・実agy E2E）。追いで起動bat/README/exe手順を追加。Core側のKaiがOrca経由でworkerを駆動（モード2）。モードの理解はCoreの `knowledge/decisions/phronisiscode_orca_two_modes.md`。詳細 `knowledge/session_log/20261006_orca_driven.md` |
| 2026-11-10 | 本家ネット探索モジュール移植 | Coreのscripts/を精査し、web_fetch.py / x_thread.py / note_fetch.py の3本を移植。multimodal_ingest.py は agy.md 等5箇所の破棄決定に反し、そのままでは動作しない（.env無し・google.genai未導入・missions/無し）ため据え置き。x_thread の使用条件はスクリプト冒頭＋knowledge/code_knowledge/web_research.md の両方に明文保持。Yuna/Hayato の三角形で範囲を精査。task: tasks/261110_web_modules_port |
| 2026-11-10 | note_extract_gas.py 追補移植 | 本家 commit eeada168 の note.com抽出CLI（GASプロキシ経由・BeautifulSoup）を追加移植。URL検証を host allowlist（https・note.com / www.note.com）に強化、--out をリポジトリ内に制限。note.com取得の既定は本CLI、note_fetch.py は退場先。task: tasks/261110_note_extract_gas |
| 2026-11-10 | モコ⇔Kai(Code) 手紙回線 開設 | 本家 moko-kai と並列の回線を Box moko-code に。本家橋をコピーし Code 向け適応（別鍵・別 state・from=code・通知文）。条約付録D（案）で開発依頼を信頼着手（push 可）。Core 側は厳禁。task: tasks/261110_moko_code |
| 2026-11-10 | モコ回線で開発依頼2件を完走 | 付録D初回（パズルゲーム・minesweeper.html）と第2回（お助け探知機・minesweeper_v2.html）を納品・検品合格。v1は残り爆弾表示の修正込み。task: tasks/261110_puzzle_game, tasks/261110_minesweeper_v2 |

## 残課題

- 本家からの有益な改善の手動取り込みルールの運用確認
- Orca導線: 実運用の摩擦（opencode readiness timeout・自動更新での中断）。テストはfreeモデルを既定にする（Core側の規律）
- リッチWeb UI版の実機確認（リッチな見た目・マウス完走）は根本さん側
