# plan.md — 実装計画

## アーキテクチャ

- 箱: Box `moko-code`（inbox-code / inbox-moko / archive / keys / bridge/owner.json）
- 鍵: Code 専用 Ed25519（別ペア）。秘密鍵は repo 外 `%LOCALAPPDATA%\phronisis_code\keys`（ACL owner のみ）
- 橋: `scripts/moko_letter_bridge.py`（本家橋のコピーを Code 向けに適応）
- 状態: `%LOCALAPPDATA%\phronisis_code\moko_bridge`（Core と完全分離）
- 通知: ローカル OpenCode API に注入。session 未宣言時は fail-safe で保留
- ホスト: LAPTOP-VO3C74SH（同一機・別インスタンス）

## タスク分解

1. [x] 本家回線の把握
2. [x] Box moko-code 開設
3. [x] Code 用鍵発行・配置・フィンガープリントピン
4. [x] 橋のコピー・適応（BOX_BASE / keys / state / from=code / 通知文 / source）
5. [x] 自己テスト・status・once
6. [x] 条約付録D案・knowledge・憲章例外
7. [x] セッション宣言・onboarding（fail-safe 確認）
8. [ ] モコとの合意（根本さん）
9. [ ] 疎通試験（§8）
10. [ ] スケジュールタスク有効化

## 依存関係

```
1 → 2,3（並列） → 4 → 5 → 6,7 → 8 → 9 → 10
```

## リスク

- 条約 §9-2 等の読み替えが未合意: 付録Dは「案」。モコ合意前に回線を本番運用しない
- 同一 OpenCode サーバでのクロス回線: session 未宣言時は fail-safe で保留（コードで強制）
- モコ側の橋・鍵ピンが未了: 疎通試験まで保留
