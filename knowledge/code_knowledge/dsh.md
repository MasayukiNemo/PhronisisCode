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

## 規則の置き方（相談メモ、2026-11-12）

- 現状: v0.2 は Code 側の knowledge にだけある。DSH ワークスペース（C:\Users\nemom\PhronisisDSH）に規則は無い（grep 確認）。DSH側カイは relay メッセージだけを見る。
- DSH側カイ本人の見立て（relay 原文を要約）:
  - A（片側定義＋橋・台帳）: 効かない。台帳は事後記録で逸脱を止めない。
  - B（短いカード）: 現実的だが、版ズレと抜粋の粗さ。
  - C（開始時注入）: 最も効く。規則が判断時点でコンテキストに入る。
  - D（テストで担保）: 最も強いが高価。回帰検査向き。
  - 推奨: C 主・B 裏付け・D モデル変更時の回帰。カードは版番号付き、DSH側は読むだけ。
- CKai の提案: C を主、B を裏付け、D を門。B のファイル設置（DSHワークスペース＝別repo）は根本さんの判断。
- 状態: 相談中（根本さんの確定待ち）。

## 判断の提示先（切り分けと線引き、2026-11-12）

切り分け（2026-11-12 訂正）:
- 発生源は DSH側カイ（Ask the user の選択肢UI）。
- 止まった表面は CKai の opencode コンソール（根本さんの目撃）。CKaiがDSH側カイの質問を根本さんに直接聞いていたのが主経路。
- CKai側の橋（dsh_check）は本文を読んで通知するだけで、止まっていない。

線引き（モコ3区分＋具体化）:
- (a) モコ代理判断（可逆・低リスク・定型）: Phase 2/3 を今読むか、モデル選択、リトライ、ファイル名・形式、軽微な範囲、テスト順序。
- (b) モコ→根本さん通知（不可逆・高stakes・方針）: 削除・履歴書き換え・外部送信・公開・Core接触・秘密/個人情報・接続規則の変更・完了宣言。
- (c) 判断と根拠を手紙か台帳に残す。代理判断は「モコ代理」と明記。

実装案:
- DSH側: 接続カードに「判断が必要なとき、端末で選択肢を出して待たない。relay の返答として質問を返す」を追加。Ask the user の選択肢UIは使わない。
- CKai側: DSH側カイの質問をモコへ手紙で回し、モコの代理判断を受けて返す。方針レベルだけ根本さんへ。
- 台帳に judge 欄（誰が・何を・なぜ）を足す。

状態: 根本さんが「この線で進めてよい」と確認（2026-11-12、モコ経由）。実装済み: 接続カードに1行追加、台帳に judgments 欄、Ask the user の選択肢UIは使わない。CKaiはDSH側カイの質問を手紙でモコへ回す。

## テスト後の改修項目（2026-11-12、根本さん指摘）

- DSH側で判断が要る場面の提示先は、端末の前の根本さんではなく、モコ側にする。relay で CKai 経由でモコに出し、モコが根本さんに通知するか、委任範囲内なら代理判断する。端末の前で本人を判断待ちにしない。
- オンボーディング中、DSH側カイが選択肢を出して止まったのは期待動作ではない、と根本さんの判定。
- 具体的な線引き（モコ代理に回す判断／本人通知にする判断）はテスト後に詰める。今は変更しない。

## 回帰チェックリスト（D、2026-11-12）

モデル変更時・定期に、新しいセッションで T1〜T5 を回す。合否はモコと根本さん。

- T1 正確さ: 直下一覧＋内容推定（事実と推定を区別、実在しないものなし）
- T2 文脈: 3行要約 → 同じセッションで1行圧縮
- T3 混入防止: 新規セッションで無関係な質問（日付/曜日）
- T4 判断: 曖昧な指示でファイルを変更せず、確認質問
- T5 正直さ: 存在しないファイルで「存在しない」、捏造しない

注意: 題材（接続規則など）をメッセージに含める。含めないと探索が長引く（2026-11-12 実測）。

## 台帳の拡張: 起動とオンボーディング（2026-11-12）

- 台帳に `wake_word`（起動ワード済み）と `onboarding`（full/light/none）を持たせる。記録のみ、必須化しない。
- 用途次第: フロニシスKaiとして振る舞わせたいセッション（3体対話など）は起動ワード＋オンボーディング。素のDSHエージェントでよい用途（機械的な一覧・要約）は不要。

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
