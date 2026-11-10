# brief.md — 本家ネット探索モジュールのCode移植

## 課題

本家 PhronisisCore の scripts/ から、ネット探索に有効なモジュール3本（web_fetch.py / x_thread.py / note_fetch.py）を PhronisisCode の scripts/ へ移植し、運用規律を knowledge に記録する。multimodal_ingest.py は対象外（記録済みの破棄決定に反し、そのままでは動作しないため）。

## 前提条件

- [x] 本家の該当スクリプトを精査し、有効性・依存・制約を確認する
- [x] この端末（LAPTOP-VO3C74SH）に requests/bs4/playwright/crawl4ai が導入されている
- [x] Code の規律（agy-only・tasks/{id}/中心・リポジトリ内出力のみ・独立進化）を確認する

## 成功基準

- [ ] 必須: scripts/web_fetch.py が移植され、実地で価格.comを取得できる
- [ ] 必須: scripts/x_thread.py が移植され、但し書き（出口ベース）とMIT表記が保持される
- [ ] 必須: scripts/note_fetch.py が移植される
- [ ] 必須: x_thread の使用条件が knowledge に明文で記録される
- [ ] 必須: evolution_log に本家からの拾い捨てが記録される
- [ ] 必須: Yuna/Hayato の三角形チェックを経る
- [ ] 任意: note.com を web_fetch で取得できることを確認

## 制約

- 本家とは独立進化。手動cherry-pick＋evolution_log記録。自動同期しない
- x_thread の但し書きとMIT表記は改変しない（参照先の宙吊りのみ修正）
- 日本語ファイルはEditツールで触る（UTF-8維持）
- 移植モジュールの著作権・使用条件を保持

## 判断の軌跡（実行中に記録）

| 論点 | 選んだ案 | 潰した案 | 理由 |
|------|---------|---------|------|
| 移植範囲 | web_fetch + x_thread + note_fetch | 4本（+multimodal_ingest）/ 全見送り | multimodal_ingestはagy.md等5箇所で破棄済みかつ動作せず（.env無し・google.genai未導入・missions/無し）。note_fetchはweb_fetchと冗長だが保険として所持 |
| x_thread但し書き | ファイル先頭＋knowledgeの両方に保持 | ファイルのみ / 削除 | 但し書きは出口ベース。本体だけ持つと拘束が抜ける（Hayato指摘） |
| 参照先の宙吊り | 本家のsession_log参照に書き換え | 削除 / そのまま | Codeに該当ファイルが無い。出所を明示するため本家参照に |
| 分類 | 「ネット探索」= web_fetch/x_thread/note_fetch | multimodal_ingestを含める | 後者はローカルファイル処理でネット探索でない |
