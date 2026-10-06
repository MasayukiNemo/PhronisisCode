# brief.md — クイズ リッチWeb UI版（グラフィカル強化・別タスク）

## 課題

既存クイズ（CLI: scripts/quiz_game.py / GUI: scripts/quiz_gui.py）の出題ロジックを再利用し、
グラフィカルでリッチなWeb UI版を別タスクとして追加する。
出題ロジックは二重実装しない。UI要件「グラフィカルでリッチ」の実現手段はKaiが判断する。

## 前提条件

- [ ] 出題ロジックは quiz_game.py を import 再利用する（DIFFICULTY / LENGTH / timeout_for / require_agy / ask_quota / fetch_questions / comment_for / base_dir / safe_console / QUOTA_STOP_THRESHOLD / DEFAULT_NUM / DEFAULT_DIFFICULTY）
- [ ] 実行時追加依存なし（Python標準ライブラリのみ。描画はOS付属ブラウザ）
- [ ] quota作法を維持（ask前に確認、core.QUOTA_STOP_THRESHOLD 以下は開始しない。値はcoreから取得し、属性が無ければ起動失敗させる。閾値を再定義しない）
- [ ] 成果物はリポジトリ内（scripts/quiz_web.py + scripts/quiz_webui/{index.html,style.css,app.js}）

## 成功基準

- [ ] 必須: `python scripts/quiz_web.py` でローカルWeb UIが起動し、127.0.0.1のURLを既定ブラウザで自動表示する（オープン失敗時はURLをコンソールに必ず表示）
- [ ] 必須: UIでテーマ（空=おまかせ）・設問数1-10・難易度4段階を設定して出題開始できる（既定: 空/5/ふつう）
- [ ] 必須: リッチUIチェック7項目を満たす（(1)動く背景 (2)ガラス調カード (3)選択/正誤の状態アニメ (4)画面トランジション (5)問数進捗 (6)結果スコア演出＋高得点confetti (7)生成インジケータ。装飾は可読性を損なわない）。判定はチェックリスト＋手動確認記録
- [ ] 必須: 回答→正誤フィードバック→解説→次へ をマウスで完走でき、最終スコアと core.comment_for の寸評が出る
- [ ] 必須: quota確認→閾値（core.QUOTA_STOP_THRESHOLD）以下は停止。agy不調・残量取得不能時はUIに明示（黙って落ちない）
- [ ] 必須: 生成中もUIが固まらない（生成は非同期ジョブ。経過秒・目安最大秒・再試行状態をポーリング表示）
- [ ] 必須: 二重実装なしの機械判定（quiz_web.py / quiz_webui に難易度表・quota閾値・comment_for・fetch_questions/valid_question の再定義が無い。grepで0件、core経由のみ）
- [ ] 必須: 結果を repo直下に quiz_<stamp>.txt で保存し（既存GUIと同事実）、UIに保存パスを表示
- [ ] 必須: HTTPセキュリティ（127.0.0.1限定 / X-Quiz-Token必須 / Host検証 / 静的配信は既知3ファイルのみ / LLM文字列はtextContentのみでinnerHTML不使用）
- [ ] 任意: 同じテーマで別セット再戦
- [ ] 任意: キーボード操作（1-4・Enter）
- [ ] 任意: UIの終了ボタン（/api/shutdown）

## 制約

- 技術スタック: Python 3.x 標準ライブラリ + 同梱HTML/CSS/JS（CDN・Webフォント不使用＝オフライン動作）
- 出題の唯一経路は core.fetch_questions（agy ask・救済・検証を迂回しない）
- 難易度表・救済（1回リトライ＋有効問のみ）・検証（valid_question）・quota作法を落とさない
- exe化は任意（PyInstallerはビルド時のみ・dist/build/*.specはgitignore）。frozen時の静的資産解決（resource_dir）だけ用意する
- 検証はstub主体（quota消費を止める）。実agy検証は残量が健全な場合のみ1回・記録する

## 判断の軌跡（実行中に記録）

| 論点 | 選んだ案 | 潰した案 | 理由 |
|------|---------|---------|------|
| UI手段 | ローカルWeb UI（stdlib http.server + HTML/CSS/JS） | tkinter Canvas / Pygame / 外部サーバ | 追加依存なしで「グラフィカルでリッチ」の到達点が最高。tkinterは表現力不足、Pygameは依存追加、外部サーバは過剰。前回web棄却（サーバ不要）を反転する代償を以下で引き受ける |
| 反転の代償 | プロセス管理・ポート・トークン・shutdownを設計で潰す | 記録せず進む | 前回は「サーバ不要」を利点に数えた。反転理由（リッチ要件の格上げ）と代償処理を明示 |
| サーバ露出 | 127.0.0.1限定 + ワンタイムトークン + Host検証 | 0.0.0.0 / トークンなし | CSRF/DNS rebindingの入口を塞ぐ。ローカル玩具でも入口を閉じるコストは小さい |
| ロジック | quiz_game.py を DI で import 再利用 | Web用に複写 | 二重実装はdriftの元。単一正本を維持（要件） |
| quota閾値 | core.QUOTA_STOP_THRESHOLD を参照 | 7を再定義 | quiz_gui.py に続く三重定義を避ける（Yuna/Hayato/Gaia指摘） |
| 進捗 | 生成=非同期ジョブ + /api/status ポーリング | 同期POST一発 | 「生成中もUIが固まらない」を実挙動で満たす。再試行表示もここから |
| 寸評/難易度 | /api/config と結果payloadで core から配布 | JSにハードコード | comment_for・難易度名の再実装を防ぐ（Gaia指摘） |
| 結果保存 | サーバ側で repo直下 quiz_<stamp>.txt に保存 | ブラウザDLのみ | 既存GUIと同事実。「成果物は手元に残る」作法を踏襲（Yuna指摘） |
| 保存整形 | core に format_result_text を追加し共有 | 各UIに複写 | 既存GUIの整形と二重化しない。単一正本を厚くする |
| 静的資産 | scripts/quiz_webui/ にHTML/CSS/JS分離、resource_dir()でfrozen対応 | Python文字列に埋込 | 可読性・保守性・exe同梱余地。リッチCSSを素直に書ける |
| ブラウザ起動 | 自動オープン（失敗時URL表示） | 手動URLのみ | 既存exeの「1手で開始」に寄せる |
| リッチ定義 | 7項目チェックリスト＋手動確認 | 「リッチ」主観のまま | 受け入れで揉めない。検証可能にする（Hayato/Yuna指摘） |
| exe | 任意（resource_dirのみ用意、ビルドはしない） | 必須化（_MEIPASS同梱） | 原文にexe要求なし。ただし配布したい時の道は塞がない |
| 検証 | stub全遷移＋HTTPセキュリティ＋手動ビジュアル。実agyは残量健全時1回 | 実agyのみ / stubのみ | stubで固まらないUIは実証不能なため、限界をlogに明記。実agy1回で真の経路を確認 |
| オフライン | CDN・Webフォント不使用、confettiはcanvas自前 | 外部CSS/フォント | オフライン動作・依存ゼロ |
| キャンセル | 世代番号(gen)＋/api/cancel | 単純な画面戻し | 破棄後に再開始できない破綻を潰す（Metis指摘） |
| 保存テーマ | job.meta（LLM命名）に統一 | 生入力 | 設定画面の生テーマではなく命名を使う既存GUIと同事実に（Metis指摘） |
| quota停止文言 | core.QUOTA_STOP_THRESHOLD を埋込 | "7%以下"の直書き | 単一正本の徹底（Metis指摘） |
| config失敗時 | 開始ボタン無効化＋再読込案内 | 空の難易度で開始可 | 「黙って落ちない」基準の底上げ（Metis指摘） |

## 検証方法（受け入れ判定）

- 自動: tasks/261006_quiz_rich/flow_test.py（coreをstub差替、port=0で起動し urllib で全API遷移・403系・結果保存・comment_for呼出を検証。quota消費ゼロ）
- 自動: `python scripts/code_health_check.py --no-color` が exit 0
- 手動: ブラウザでリッチ7項目とマウス完走を確認（根本さん実機。stubモードでも可）
- 実agy: 残量健全時のみ1回、出題経路を確認しログに残量を記録

<!-- status: complete | agent: kai -->
