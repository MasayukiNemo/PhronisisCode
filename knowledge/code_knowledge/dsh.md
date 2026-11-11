# DSH（DeepSeek Harness）bridge

DSH はこの端末で稼働する Web UI（127.0.0.1:3080）。DSH 側カイと対話する。本家 PhronisisCore の bridge を Code に移植済み（2026-11-11）。

## 構成

- 本体: スケジュールタスク `PhronisisDSH`（`C:\Users\nemom\PhronisisDSH\start_dsh.cmd`）が node で `dsh web` を起動
- 認証: トークン。`%LOCALAPPDATA%\PhronisisDSH\start.out`（毎回 `.prev` にローテーション）。`dsh_common.find_token()` が検出
- スクリプト（`scripts/`）:
  - `dsh_common.py` — トークン検出・URL・セッションオープン・本文保存
  - `dsh_send.py` — メッセージ送信
  - `dsh_check.py` — 最新応答を `scratch/dsh_reply.txt` に保存
  - `dsh_answer.py` — Ask the user の択一に回答

## 使い方

```
python scripts/dsh_list.py [--workspace PhronisisDSH] [--json]
python scripts/dsh_send.py -m "本文" --uuid <uuid> [--workspace PhronisisDSH]
python scripts/dsh_check.py --uuid <uuid> [-o 出力先]
python scripts/dsh_answer.py -o "選択肢" --uuid <uuid>
```

- 宛先は UUID で指定する（接続規則 v0.2 §2）。`--session`（名前部分一致）は互換用。引数なしは開かない（一覧を出して止める）。
- 台帳に無い UUID は拒否する。発見手順のみ `--allow-unlisted`。
- 台帳: `knowledge/code_knowledge/dsh_sessions.json`
- 接続規則: `knowledge/code_knowledge/dsh_connection_rules.md`

## Code適応（2026-11-11）

- `dsh_common.find_token` に現行ランチャーのログ（`%LOCALAPPDATA%\PhronisisDSH/start.out` と `.prev`、`start.log`）を追加。
- `dsh_common.dismiss_modals` を追加（DSH 0.2 のプレビュー通知モーダル対策）。
- それ以外は本家ロジック不変。旧パス（`%TEMP%\dsh_out*`）は互換のため残置。

## 稼働

- DSH v0.1.2-rc.1（`%APPDATA%\npm\node_modules\@deepseek-ai\dsh`）
- タスク `PhronisisDSH`（`C:\Users\nemom\PhronisisDSH\start_dsh.cmd`）

## 既知の状態（2026-11-11）

- DSH 0.2 のプレビュー通知が `role=dialog` + mask でクリックを遮る。`dsh_common.dismiss_modals()` が起動後に「続ける」を押して閉じる（出現遅延に備えて最大6秒待つ）。
- 過去の失敗 `UNKNOWN_MODEL "muse-spark-1.3-contributor"` は、モデルを DeepSeek V4.1 Flash に変えて解消。
- 疎通往復は成立: `dsh_send` → DSH側カイが「OK」→ `dsh_check` で確認（2026-11-11 23:21）。

## 疎通テスト結果（2026-11-12）

- UUIDピン留め: PASS。`--uuid` で正しいセッションを開く（f567c0cb）。台帳外・存在しない UUID は拒否し、名前一致へフォールバックしない。
- 新規/継続: 継続は PASS（UUID）。新規（`--new`）は部分PASS。メッセージは空セッションに届くが、DSHのdraft設計により「新規ボタンが作る空セッション」と「実際に送信される空セッション」が1つずれる。`--new` の後は実送信先の UUID を確認して台帳に登録する。
- ワークスペース: PASS（PhronisisDSH）。未追加の PhronisisCode は拒否（追加済みのみ）。
- relay定型: PASS。定型で送信 → 「受領」が原文で返る。
- 失敗系: 部分PASS。開けない宛先・台帳外UUIDは止めて報告（名前一致に逃げない）。失敗文言の自動検知は未実装（本文を読む）。
- モデル: LongCat 2.5 Free（セッション設定。変更されうる）。

## モデル選択の材料（2026-11-12）

- セッションのモデルは LongCat 2.5 Free（無料）。根本さんの操作で変更された。
- 観察: 同じモデルで OpenCode ではエラーが出るが、DSH では出ていない。
- 根本さんの見立て: 「うまく組み合わせれば知能とトークン節約が両立する」。
- 台帳の `model` 欄に記録する（§10 の軽微な運用メモとして項目追加）。

## 注意

- DSH UI は共有リソース（DSH側カイ）。乱打しない
- 送信 → 応答確認で1往復。完了は応答の確認
- 応答は `scratch/dsh_reply.txt` を Read で読む（cp932対策）
- トークンが見つからない場合は `%LOCALAPPDATA%\PhronisisDSH\start.out` と `.prev` を確認
