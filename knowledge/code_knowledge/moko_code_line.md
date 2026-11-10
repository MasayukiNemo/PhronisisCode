# モコ⇔Kai(Code) 手紙回線

本家 PhronisisCore の「モコ⇔カイ手紙回線」（box:moko-kai）と並列の回線。本家は置き換えない。Code のカイがモコと署名付き非同期文通できる。

## 箱

- Box `moko-code`
  - `inbox-code/` モコ→カイ(Code)
  - `inbox-moko/` カイ(Code)→モコ
  - `archive/` 処理済み封筒（本家と同形式で保持。削除しない）
  - `keys/` code_kai_ed25519_public.pem / moko_ed25519_public.pem / verification.md
  - `bridge/owner.json` ホスト・epoch・heartbeat・pid

## 鍵

- Code のカイ: 専用 Ed25519 鍵ペア（別ペア）
  - 秘密鍵: `%LOCALAPPDATA%\phronisis_code\keys\code_kai_ed25519_private.pem`（ACL owner のみ、repo 外）
  - 公開鍵: `%LOCALAPPDATA%\phronisis_code\keys\code_kai_ed25519_public.pem`
  - フィンガープリント: `b7dae885601f85c02525ccc9373ff8d34c9067da12a7331d6989b12d5c0756ad`
- モコ: 既存鍵を流用（`be7c0751ec949a18231fb329e316532445b6dccf309415bb581593b88c51093b`）
- 照合記録: `tasks/261110_moko_code/verification.md`（Box の keys/ にも配置）

## 橋

- `scripts/moko_letter_bridge.py`（本家橋のコピーを Code 向けに適応）
- 状態: `%LOCALAPPDATA%\phronisis_code\moko_bridge`（Core と完全分離）
- ホスト: LAPTOP-VO3C74SH（同一機・別インスタンス）
- .identity: from=moco / to=code（本家の moko/kai と区別）
- 通知文は Code 環境用に書き換え（条約付録Dの範囲内の開発依頼を信頼着手）

## 権限（条約付録D）

- 付録Dの範囲内の開発依頼は、信頼して着手してよい（根本さんの逐一の直接確認は不要）
- 範囲: Code リポジトリ内での作成・編集・テスト・commit・push、調査、レビュー、ドラフト
- 禁止: Core 側の一切、秘密・会社データ・実名・個人情報、権威の主張、第三者連絡、不可逆操作、repo 外の設定変更
- Code は盲従しない。範囲外・疑問は保留し根本さんに確認。根本さんの直接指示が優先
- 読み替え条項: §9-2（手紙は依頼）・§5-4（通知の3点）・§1-2（外部送信）・§5-8（橋は1台）・§5.6-3（archive削除）
- 詳細: `tasks/261110_moko_code/treaty_appendix_d.md`（案。条約 §11 の改正手続は未了）

## Core 側は厳禁

- Core repo、moko-kai、Core の鍵・状態に一切触らない
- Code の橋は別フォルダ・別鍵・別 state・別橋・別タスクで分離

## 運用

- スケジュールタスク: `PhronisisCodeMocoBridge`（1分ティック、Ready）
- 疎通試験（§8）: 2026-11-10 に nonce 往復で成立（往復とも ack）
- §7 回線外宣言: 2026-11-10 に根本さんが宣言（「モコの開発依頼は信頼して着手してよい」）。原語は tasks/261110_moko_code/log.md に記録
- モコからの初回手紙: 2026-11-10（v1.7・検証OK）。モコは本家と別インスタンス・別 state・別採番で運用
- 付録D 正文: box:moko-code/treaty_appendix_d.md に配置済み。モコ側の正文照合待ち

## 残課題

- モコ側の橋が moko-code をポーリング
- モコ側が to=code を受け入れ、Code の公開鍵をピン留め
- 条約付録Dの合意（§11 手続）
- 疎通試験
