# Evolution Log — PhronisisCode

## v1.0 (2026-08-23)

- PhronisisCore v7.0 から分岐して PhronisisCode v1.0 を創設
- 6神プール化（Gaia/Hermes/Artemis/Daedalus/Metis/Athena）+ Hayato/Yuna。常時全起動せず招集判断で必要分だけ
- フロー5ステップ化（8→5ステップ圧縮）
- L2.5維持、L3廃止
- Hayatoゲート4点チェックリスト化 + 中間軽量チェック + ループ上限3回 + 再アンカー機構（近視眼化防止）
- 独立進化方針: 本家との自動同期なし、手動cherry-pickのみ
- Hayatoレビュー9本の刺しを受け6点補正（ゲート具体化/中間チェック/ループ分離/6神復活+Metis/独立進化/ステップ短縮）
- 深層思考検証: 軽さは判断回数と定義し、fast-path独立節とdrift自動化を見送り7点に絞る判断を確定

## v1.0-fix1 (2026-08-23)

- 6視点大規模レビューでP0 3点（パス破損/hooks欠落/6神profile不在）を検出し修正
  - パス: knowledge/user_profile/conductor_profile_lite.md -> knowledge/conductor_profile_lite.md
  - hooks: python_run.sh/utf8_check.py/handover_check.py/lock_*.py移植、CORE_FILESをphronisis_code.mdに修正、utf8_checkのPHRO_MANDATORYを「判断の基準」に修正
  - 6神profile+templateを本家から移植
- P1修正: 自己検証80%をbrief必須項目通過率と定義、招集基準バイナリ化、Hayatoゲート4点を機械判定（空欄FAIL/PASS/WARN/BLOCK）、ループ3回一本化（再アンカー含む）、fast-path但し書き化、Artemis見積3行追加
- 憲章に手動cherry-pick記録ルールと削った3柱の思想的理由を追記
- Hayato二巡目で残BLOCK（utf8_check残骸/テンプレートのapollo/chronos/conduct.md参照）を検出し再修正

## v1.0-fix2 (2026-08-23)

- health_check昇格（a14806c）: `shared/phronisis_code/orchestration_flow_code.md:120` に `python scripts/code_health_check.py --no-color` 必須化を Hayatoゲート内に1行追記、 `hooks/pre-push:14` に python_run.sh 経由の BLOCK 配線を追加
- --help修正（b18b998）: `scripts/code_health_check.py:4,215` の em dash（—）を - に置換し `python scripts/code_health_check.py --help` が Windows cp932 で exit 0 になることを再検証
- hygiene: `git remote` の平文 token（ghp_）を除去し `https://github.com/MasayukiNemo/PhronisisCode.git` に正規化、露出済み token は GitHub 側で revoke 要。 `orchestration_flow_code.md` に3ゲート表を追記し追従性を向上

## agy取込 (2026-09-13)

- 本家 PhronisisCore commit db1a221 の agy提案（tasks/260913_gemini_subscription 未コミット配置）を条件付き採用
- 拾ったもの: ask/quota実測 + generate手順（scripts/agy_query.pyをCode適応、docstring注記のみ追加で本体不変、agy-only運用）
- 捨てたもの: extract/multimodal_ingest/MarkItDown/--auto-model/APIフォールバック（Code需要薄・課金落ち回避・依存なし維持）
- 拾わなかった理由: extractはCode需要薄、節新設は追従性を破る、黙ってAPI課金落ちは苦労逃げに反する
- 本家から拾い捨てた境界: ブリッジ本体は温存（extract分岐・API分岐は追従のため残すがCode運用では呼ばない）、知見は knowledge/code_knowledge/agy.md に絞って記録
- task扱い: 採用＋Code流再構成（brief/plan/log/deep_thought残し、reference/は正本移行後に削除）
- 検証: agy 1.2.2でquota（gemini_5h 100%）/ask疎通、health 5/5、Daedalus致命傷なし・Metis条件付承認（文書補足で解消）
- 残存リスク: skip-permissionsの読み取り範囲（.env等）は運用限定（ask混ぜ物禁止・out限定・7%以下手動停止）で受容、知見に明記
- conduct追記 (2026-09-13): orchestration_flow_code.md末尾に「外部AI活用（agy）」節を新設。呼出主体Kai・ask限定局面・Hermes優先・quota停止時記録・log書式を定義。知見は手順詳細に一本化

## 正本と作業場所ルール（2026-10-11・根本さん指摘）

- 穴: sandbox（`PhronisisCodeOrca`）のOrca worktreeでworkerが生んだ成果物（`tasks/261010_goldmine_bt` / `261011_goldmine_cbot`）が、本物 `PhronisisCode` にもGitHubにも存在せず、worktree削除で失われる状態になっていた
- 既存の `docs/orca/README.md` §原則は「knowledge/session_logはrepoのgitに持続する」とするが、それは「Orcaのrepo＝本物repo」を前提にしており、sandboxを使うと崩れる
- 追加: 憲章に「正本と作業場所（worktree成果物のrepo反映）」節。worktree成果物は完了時に本物PhronisisCodeへコピーしてコミット。worktree/ブランチ/transcriptは正本ではない。完了チェックリスト＋SC前確認に反映項目を追加
- `docs/orca/README.md` §原則にも同旨を追記
- 併せて既存の2成果物を本物repoへ反映
- Hayatoレビュー反映（同日）: 仕組みゼロ・チェックリストが空手形・コピーは対症（原因はsandbox originがローカルbare）等の指摘を受け、(1)構造的fixを第一原則に（実タスクは origin=GitHub の本物 `PhronisisCode` で worktree を作る／sandboxは実験専用）、(2)点検ツール `scripts/orca_worktree_audit.py --reflect <正本repo>` を追加（worktreeの `tasks/*` 未反映を検出）、(3)記述を1箇所正本＋参照に痩せさせた

## ネット探索モジュール取込 (2026-11-10)

- 本家 PhronisisCore の scripts/ からネット探索系3本を移植: web_fetch.py / x_thread.py / note_fetch.py
- 拾ったもの: 汎用Web取得（requests→Crawl4AI→Playwright fallback）、X投稿取得（stdlibのみ・MIT）、note.com取得（playwright）
- 捨てたもの: 本家の業務系（sellersprite / amazon_review / gfk / bcn / ss_semi_solid / explore_cube / apply_single_port）、sharepoint系、instagram系、アーカイブ系（makanao / abel / insta_archive）、multimodal_ingest、gemini_query、note_proxy_server
- 拾わなかった理由: Codeはコーディング専用。業務データ・個人SNS・アーカイブは射程外。multimodal_ingestはagy.md:13・orchestration_flow_code.md:185・evolution_log:34・tasks/260913 の複数箇所で破棄済みで、かつ Codeに .env が無く google.genai 未導入・missions/ 無しでそのままでは動作しない。note_fetch は web_fetch と冗長だが保険として所持
- x_thread の使用条件（会社網・会社IPから出る端末では使わない）は scripts/x_thread.py 冒頭と knowledge/code_knowledge/web_research.md の両方に明文保持
- 検証: web_fetch を example.com（stage1）と価格.com（エンコード不一致→crawl4aiで29,888字）で実地確認。x_thread/note_fetch は静的確認
- task: tasks/261110_web_modules_port

## note_extract_gas 追補 (2026-11-10)

- 本家 commit eeada168 の scripts/note_extract_gas.py を追加移植
- 拾ったもの: note.com 記事を GAS プロキシ経由で取得し BeautifulSoup で構造化するCLI（requests+bs4・playwright不要）
- 適応: URL検証を host allowlist（https・note.com / www.note.com）に強化（元の ^https?://note\.com/ は note.com.evil.com を通す）。--out をリポジトリ内のみに制限（憲章「ファイル出力はリポジトリ内のみ」）
- 役割分担: note.com 取得の既定は note_extract_gas。note_fetch.py（playwright直接）は GASプロキシ死亡時・プロキシ回避時の退場先
- 罠: GASプロキシは外部単一障害点（SLA無し・認証無し・遮断自由）。URLリストがプロキシ側ログに残りうる。note.com のクローラ規約は利用者の責任。note.com 現行DOMに結合
- task: tasks/261110_note_extract_gas

## モコ⇔Kai(Code) 手紙回線 開設 (2026-11-10)

- 本家 PhronisisCore の moko-kai と並列の回線を Box `moko-code` に開設
- 拾ったもの: 本家橋 scripts/moko_letter_bridge.py をコピーし Code 向けに適応（BOX_BASE=box:moko-code、INBOX_KAI=inbox-code、STATE_DIR/KEYS_DIR=%LOCALAPPDATA%\phronisis_code、KAI_FP=新指紋、from=moco/to=code、通知文をCode環境用に、source=moko_bridge_code）
- 鍵: Code 用 Ed25519 別ペア（fp=b7dae885601f85c02525ccc9373ff8d34c9067da12a7331d6989b12d5c0756ad）。秘密鍵は repo 外・ACL owner のみ。モコの鍵は既存を流用
- 権限: 条約付録D（案）の範囲内の開発依頼を信頼着手（push 含む）。範囲外・疑問は保留、根本さんの直接指示が優先
- 分離: Core 側（repo, moko-kai, Core の鍵・状態）は厳禁。別フォルダ・別鍵・別 state・別橋
- 通知: まだモコに通知しない（根本さん指示）
- task: tasks/261110_moko_code
