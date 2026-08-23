# brief.md — Hygiene 3点（P1/P2）

## 課題

P1（token平文/evolution_log未運用）とP2（3ゲート可視化）の衛生対策をまとめて行い、Codeの追従性と安全性を上げる。

## 背景

v1.0出荷直前で hygiene 評価を行い、P1 2点とP2 1点が残った。いずれも軽微だが、手続きの透明性と安全性に直結するため、Hayatoレビューを回しながら一括で潰す。

## 前提条件

- [ ] 憲章とフローに準拠、L2.5で回す（推論で進めて実行済み時制、24h差し戻し可）
- [ ] 6神はプール。必要時のみ招集し、呼ばなかった理由を軌跡に残す
- [ ] 2ループ目の再アンカー必須（大局観維持）
- [ ] 既存の health_check ゲートを壊さないこと

## 成功基準

### 必須

- [ ] `git remote -v` の平文 token を除去し、`https://github.com/MasayukiNemo/PhronisisCode.git` に正規化すること。露出済み token の revoke 要否を log に明記すること
- [ ] `shared/phronisis_code/protocol/evolution_log.md` に v1.0-fix2 として health_check昇格（a14806c + b18b998）と hygiene の記録を追記すること
- [ ] `shared/phronisis_code/orchestration_flow_code.md` の Hayatoゲート節末尾に3ゲート（pre-commit/pre-push handover/pre-push health）の責務分担を1表（3行程度）で追記すること
- [ ] `tasks/260823_hygiene/plan.md` と `log.md` を作成し、判断の軌跡を記録すること

### 任意

- [ ] token revoke 手順を knowledge/ に残す

## 制約

- 技術スタック: bash/git のみ。外部依存なし
- 新規ファイルは tasks/260823_hygiene 配下以外に作らない（evolution_log と orchestration_flow の追記は例外）
- 自己検証80%は「必須3項目のうち3つが手動確認できたこと」と定義（3/3=100%で80%超過）
- 出力先制約を守ること

## 判断の軌跡（実行中に記録）

| 論点 | 選んだ案 | 潰した案 | 理由 |
|------|---------|---------|------|
| token除去: remote書き換え vs token維持 | 書き換え（平文化） | 維持 | Honestとセキュリティ致命傷を優先。平文はログに残り続けるため除去、revokeをlogに明記 |
| evolution_log記載粒度 | 要約（v1.0-fix2 1エントリ） | 詳細列挙 | 追従性を優先。本質はhealth_check昇格の閉じ方で詳細はgit logで追える |
| 3ゲート表の置き場所 | Hayatoゲート節末尾 | 別章新設 | 文脈が近く追従性高い。概念の過剰分類を避ける |
| 招集判断: Gaia を呼ぶか | 呼ばない | 呼ぶ | 設計2案は深層思考で収束、アーキテクチャ分岐なし |
| 招集判断: Hermes を呼ぶか | 呼ぶ（Kai代行） | 呼ばない | remote/evolution_log/orchestration_flowの現行状態を事実確認する必要 |
| 招集判断: Artemis を呼ぶか | 呼ばない | 呼ぶ | 変更3ファイルで依存単純、タスク分解の要なし |
| 招集判断: Daedalus を呼ぶか | 呼ぶ（Kai代行） | 呼ばない | token除去とhooks/フロー編集が核、安全性視点必須 |
| 招集判断: Metis を呼ぶか | 呼ぶ（Kai代行） | 呼ばない | 実装を伴うタスクは原則招集、表の可読性が論点 |
| 招集判断: Athena を呼ぶか | 呼ぶ（Kai代行） | 呼ばない | 3つの衛生対策を統合し一括で収束 |

## 検証方法

1. `git remote -v` に token 文字列（ghp_）が含まれないこと
2. `git status` が clean であること
3. `shared/phronisis_code/protocol/evolution_log.md` に v1.0-fix2 の記述があること
4. `shared/phronisis_code/orchestration_flow_code.md` に3ゲート表があること
5. `tasks/260823_hygiene/log.md` の自己検証が80%以上であること
6. Hayatoゲート4点が PASS/WARN であること

## 備考

- Hayatoレビューを回しながら進めること（中間軽量チェック + 最終ゲート）
