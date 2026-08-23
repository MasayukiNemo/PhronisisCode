# deep_thought.md — 自己検証昇格 深層思考（Kai）

## 問い直し: なぜヘルスチェックをゲートに昇格するのか

駆動試験はHayato4点をPASSしたが直後に --help がcp932で落ちた。ゲートは「仕様に忠実か」を静的に見たが「実際に動くか」を機械で見なかった。これが近視眼。コードが自身を検証する閉じ方を手続きに刻むことで、次回から宣言と実体の乖離を人手レビューではなく実行で担保する。これが大局観。

## 判断OS照合

- 思想的一貫性: 宣言と実体の一致はPhronisisCodeの核。手続きに機械検証を埋め込むのは思想の体現。
- 本質的シンプルさ: 追記は1-2行でよい。過剰な機構を嫌う。新規概念は要らない。既存の health_check を流用するのが最もシンプル。
- 追従性: 人間が読んで分かる1行。hooks配線は bash/python_run.sh 経由で既存パターンを踏襲。
- 実用との均衡: pre-pushでBLOCKすると作業が止まる摩擦 vs WARNだと見逃す。どちらを選ぶかが分岐点。

## 2つの論点の構造分解

### 1. 配線先: pre-push vs pre-commit

- pre-commit: コミット毎に走る。早期検出だが頻度が高く、失敗時の摩擦が大きい。現行pre-commitはutf8_checkのみで軽量。health_check（5検査）は軽量だが追加するとコミットコストが上がる。
- pre-push: push時のみ。頻度が低く摩擦が小さい。現行pre-pushはhandover_checkで既に重め。health_checkを追加してもpush頻度は低いので許容。根本さんの「苦労はできるだけ逃げろ」にも合う。頻度の低い関門で確実に止めるのが筋。
- 結論仮置き: pre-push 推奨に従い pre-push を選ぶ。失敗時の扱いは後述。

### 2. 失敗時の扱い: WARN vs BLOCK

- WARN: 警告を出すがpushは通す。作業を止めないが、見逃されるリスク。駆動試験のように後で気づく近視眼が残る。
- BLOCK: 失敗時はpushを止める。宣言と実体の一致を機械で強制できる。ただし誤検知で作業停止のリスク。health_checkはファイル存在等の厳格チェックで誤検知は少ない。BLOCKの方が思想的一貫性に忠実。
- ただしCodeの現行哲学は「Hayatoゲートは手続き検証+致命傷検出」に絞る。health_checkが落ちるのは致命傷に近い（参照破損等）。BLOCKが妥当だが、初期導入でいきなりBLOCKは摩擦が高い。
- Yunaへの問い: 根本さんは WARN と BLOCK のどちらに違和感を覚えるか。Bに照らすと「止めるべき時は止める」が好みか。
- 仮置き: WARN を選びつつ、メッセージで BLOCK 相当の警告を明記し、将来BLOCKへ昇格できる余地を残す。もしくは BLOCK を選び、health_check失敗を明示する。判断OSの「選ぶことは捨てること」でどちらかを切る必要がある。

深層思考の現時点案: pre-push に WARN で配線。理由は「まずは friction を下げて定着させ、BLOCKは次の進化で」。これは端折りではなく段階導入。

### 3. --help 修正: em dash 置換 vs エンコーディング対策

- em dash 置換: 根本原因は argparse description に含まれる — がcp932にない文字。置換すれば即解決。最もシンプル。
- エンコーディング対策: stdoutをutf-8に再設定、PYTHONIOENCODING、printのerrors='replace' 等。根本解決に見えるが、リポジトリ全体の文字コード問題を広げる。過剰。
- 結論: 置換を選ぶ。既に b18b998 で置換済み。再検証のみ行う。

## 実装方針

- orchestration_flow_code.md: Hayatoゲート節の直後 or 完了宣言の直前に1-2行追記。例: 「Hayatoゲートに加え、python scripts/code_health_check.py --no-color が exit 0 であることを必須とする」。追記位置はフロー図の [4] Hayato検証 の節内が自然。
- hooks/pre-push: 既存 handover_check の後に health_check 呼び出しを追加。bash "$HOOK_DIR/python_run.sh" "$PROJECT_DIR/scripts/code_health_check.py" --no-color を実行し、失敗時は echo WARN + exit 0（WARN）または exit $HEALTH_EXIT（BLOCK）。どちらかを明記。
- em dash: 既に - に置換済み。git diffで確認し、--help がcp932で通ることを再検証。
- 駆動試験のplan.mdは本タスクで触らない。スコープを広げない。

## リスク

- hooksでhealth_checkが毎回走ることでpushが遅くなる → 軽量（5検査のみ）なので影響小。
- Windowsで bash 経由の python_run.sh がhealth_checkを見つけられない → PROJECT_DIR/scripts で絶対パス指定で回避。
- orchestration_flow追記が冗長になる → 1-2行に抑える。

## 次のアクション

深層思考完了。Yunaに回す。
