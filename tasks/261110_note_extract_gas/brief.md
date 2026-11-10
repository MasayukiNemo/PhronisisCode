# brief.md — note_extract_gas.py のCode移植

## 課題

本家 PhronisisCore の scripts/note_extract_gas.py を PhronisisCode の scripts/ へ移植し、note.com取得の軽量経路として knowledge に位置づける。

## 前提条件

- [x] 本家の commit eeada168（根本さん自身の追加）を確認
- [x] この端末に requests/bs4 が導入されている
- [x] GASプロキシ経由の実地取得が成功（method=DOM、UTF-8 clean）

## 成功基準

- [x] 必須: scripts/note_extract_gas.py が移植され、実地で note.com 記事を取得できる
- [x] 必須: URL検証が host allowlist（https・note.com / www.note.com）に強化される
- [x] 必須: --out がリポジトリ内のみに制限される
- [x] 必須: GASプロキシ依存・退場経路・note.com規約/プライバシーが knowledge に明文記録される
- [x] 必須: note_fetch.py との役割分担（正規/退場先）が knowledge に明記される
- [x] 必須: Yuna/Hayato の三角形チェックを経る
- [x] 必須: evolution_log に拾い捨てが記録される

## 制約

- 本家とは独立進化。手動cherry-pick＋evolution_log記録
- 日本語ファイルはEditツールで触る（UTF-8維持）
- 移植モジュールの著作権・使用条件を保持

## 判断の軌跡（実行中に記録）

| 論点 | 選んだ案 | 潰した案 | 理由 |
|------|---------|---------|------|
| URL検証 | host allowlist（https・note.com / www.note.com） | 元の prefix 一致 ^https?://note\.com/ | 元は note.com.evil.com を通し、第三者プロキシへ任意URLを叩かせ得る（Hayato指摘） |
| --out | リポジトリ内のみに制限 | 無制限 | 憲章「ファイル出力はリポジトリ内のみ」。agy_query と揃える |
| note取得の正規経路 | note_extract_gas（軽量・構造化）を既定、note_fetch を退場先 | note_fetch を正規のまま | playwright不要端末でも動く。GASプロキシ死亡時は note_fetch へ降格 |
| プロキシ依存の開示 | web_research.md の罠に明文 | コードに留める | 単一障害点・プライバシー・規約を利用者に見せる |
