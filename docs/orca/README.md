# Orca導線（任意・Orca非必須）

> Orcaは任意の実行基盤。PhronisisCodeはOrca無しでも5ステップを回せる。この文書は「Orcaを使う場合」の手順と原則を示す。Orcaは開く場所であって、PhronisisCodeの定義ではない。

## Orcaとは

stablyai/orca（ADE = Agent Development Environment）。任意のCLIエージェント（opencode等）を git worktree ごとに並列で走らせ、一箇所で管理する。worktree・ターミナル・diff・PR・遠隔・モバイルをまとめる。MIT・OSS。モデルは持たず、既存サブスクを持ち込む（BYO）。

## なぜ載せるか

PhronisisCodeは判断フロー（課題確定→前提検証+トライアングル→実装+検証→Hayato検証→確定）を持つが、実行環境（並列worktree・diff・遠隔）を持たない。Orcaはその逆。補完関係にある。コーディングの成果（動く・レビュー済み・マージ済み）はOrcaの本領と一致し、不足する判断層をPhronisisCodeのHayato・神々が埋める。

## 5ステップの写像

| ステップ | PhronisisCodeが担う | Orcaが担う |
|---------|--------------------|-----------|
| 課題確定 | `tasks/{id}/brief.md` に構造化（成功基準） | project登録。`orca worktree create --name {task}` でタスク単位の隔離環境 |
| 前提検証＋トライアングル | 深層思考Kai・Yuna照合・Hayato刺突（サブエージェント） | コーディネータ端末をホストするだけ。検討はKaiセッション内で完結 |
| 実装＋検証 | Artemis/Daedalus/Metis等を招集。自己検証80% | worker worktreeで並列実装。diff viewer。annotate AI diff |
| Hayato検証 | 4点バイナリチェック。`scripts/code_health_check.py` | diffをHayatoエージェントがレビュー。annotateで指摘を戻す |
| 確定 | チャット出力。SC。knowledge記録 | コミット/PR。持続はrepoのgitが担う |

## セットアップ

1. Orcaを導入する（例: winget `StablyAI.Orca`。署名はSignPath Foundation）
2. このリポジトリをOrcaに登録する: `orca repo add --path <このrepo>`
3. worktreeを作る: `orca worktree create --repo "path:<このrepo>" --name <task> --agent opencode`
4. workerのモデルは起動時に指定する（`opencode -m provider/model`）。本体 `opencode.json` の既定モデルは変えない（非Orca端末のKaiの知能を下げないため）
5. Orcaの権限を Manual に倒す（Settings → Agents → Agent Permissions）。Orcaの既定は権限バイパス（yolo）
6. git identityはcloneに引き継がれない。このcloneにローカル設定する（`git config user.name/email`）
7. worktreeの重複排除（任意・推奨）: `orca.yaml` の `worktree.sharedDirectories` が `.opencode/node_modules`（worktreeごとに約52MB展開される）を共有する。Orcaの仕様で「primary checkout に実在するgitignore済ディレクトリ」のみ共有されるため、**このcloneの primary に `.opencode/node_modules` を用意**しておく（opencodeを1回起動するか、`~/.config/opencode/node_modules` をコピー）。無い端末では共有されず各worktreeで52MB複製される（警告は出ない）。背景: `knowledge/decisions/worktree_overhead_policy.md`

## 原則: Orcaの作法に呑まれない

Orcaの世界観は「worktreeは使い捨て・権限yolo・会話はOrca側（opencode.db）に散る」。この中でもPhronisisCodeの作法を維持する。

- brief / plan / log を必ず作り、判断を残す
- Hayatoゲート（4点バイナリ）を通す
- knowledge / session_log は repo の git に持続する（worktreeの使い捨てに流されない）
- Orcaの transcript を正本にしない。判断の正本は repo 側に書く
- 権限はManualを維持する

## 運用メモ（実測の摩擦）

- タスク送信は、opencodeの初回初期化（`.opencode` セットアップ）完了後に送る。早すぎると入力を取りこぼす
- opencodeのreadiness検出はタイムアウトしうる（Orcaの監督下worker）。コーディネータは「worktree作成＋terminal send」で直接駆動すると安定する
- モデル分け: worker＝安いモデル、司令＝通常モデル。per-task / per-roleで分ける
- worktreeは `C:\Users\<user>\orca\workspaces\<repo>\<name>` に作られる
- 共有ディレクトリ（`.opencode/node_modules`）は junction で共有される。worktree削除は `orca worktree rm` を使う（生の再帰削除はjunctionを辿りリンク先を消す恐れ）。詳細: `knowledge/decisions/worktree_overhead_policy.md`

## ロールアウト

コーディング・分業する端末に限る。全端末には広げない。Orcaは任意で、無くてもPhronisisCodeは回る。

<!-- status: complete | agent: kai -->
