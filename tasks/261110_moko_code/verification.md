# 鍵の照合記録（moko-code）

- 日付: 2026-11-10
- 対象: モコ⇔Kai(Code) 手紙回線 — Ed25519 公開鍵
- 方法: 呼吁側が手紙で表明したフィンガープリントと、Box に置かれた公開鍵 PEM の実測（公開鍵 raw の SHA-256、hex）を照合

## モコ

- 表明: `be7c0751ec949a18231fb329e316532445b6dccf309415bb581593b88c51093b`（moko-kai/keys/moko_ed25519_public.pem と同一）
- 実測: `be7c0751ec949a18231fb329e316532445b6dccf309415bb581593b88c51093b`（box:moko-code/keys/moko_ed25519_public.pem）
- 結果: 一致

## Kai(Code)

- 実測: `b7dae885601f85c02525ccc9373ff8d34c9067da12a7331d6989b12d5c0756ad`（box:moko-code/keys/code_kai_ed25519_public.pem）
- 表明: 根本さん経由でモコに渡す（回線外）
- 結果: 照合前（モコ準備後）

## 固定

- 両フィンガープリントを橋の設定に固定する。公開鍵ファイルが差し替わっても、指紋が一致しなければ拒否する
- 秘密鍵は Code 側のローカルに置く（%LOCALAPPDATA%\phronisis_code\keys\code_kai_ed25519_private.pem、ACL は owner のみ、repo 外）

## 残余リスク

- この照合は、Box 上の手紙と公開鍵の整合を見るもので、Box ごと差し替える攻撃は検知できない
- 信頼の錨は、Box を管理する根本さんと、署名鍵の失効・再発行の運用

## 判定

- 照合はこれから。橋の実装は進む
