# deep_thought.md — 駆動試験 深層思考（Kai）

## 問い直し: このタスクは何を試しているか

表層は「health_check CLIを作れ」だが、本質は「Codeの思想がコードに落ちているか」を自己参照的に検証する試運転である。
- 大局観維持: 5検査が briefの成功基準に忠実か。思想がチェック項目に落ちているか。
- 近視眼防止: 単なるファイル存在チェックで終わらず、参照破損・JSON妥当性・必須フィールド等の意味的検証まで届くか。
- 端折り防止: 例外でクラッシュせず FAIL 報告する、exit code、--verbose/--json等の任意要件の扱いまで丁寧に。

## 判断OS照合（conductor_profile_lite.md）

- 本質的一貫性 > シンプルさ > 追従性 > 実用の順で優先。思想を削らない。
- 「本質抽出・概念優先・抽象度往復」: まず5検査の共通構造を抽出し、具体実装で往復する。
- 「選ぶことは捨てること」: 5検査の実装案は複数あるが、外部依存なし・Python標準のみで完結を選び、外部ライブラリや過剰な抽象は捨てる。
- 「端折るな」: 省略と端折りは別。色付き等の任意要件は削るのではなく「実装するがデフォルトはシンプル」として両立する。

## 5検査の構造分解

1. conductor_profile_lite: path存在 + 参照破損なし。参照破損とは？ ファイルが空でない、かつ想定される見出し（例: 判断OS/B-Side 等）を含むか。厳格すぎると壊れやすいので、最低限「ファイル存在+サイズ>0+markdown見出し含む」で判定する。
2. hooks依存: 6ファイル（python_run.sh, utf8_check.py, handover_check.py, lock_acquire.py, lock_check.py, lock_release.py）が揃っているか。ワイルドカード lock_*.py は具体的に3ファイルに展開して検査する。
3. 6神プロファイル: 6パス（gaia/hermes/artemis/daedalus/metis/athena）の profile.md 存在。
4. opencode.json: JSON valid + agent定義が8つ。agentキーの下に8エントリあることを数える。
5. template必須フィールド: brief.md と log.md が「成功基準/軌跡表/自己検証欄」等のキーワードを含むか。キーワードの有無で判定する。厳密なパースは不要、追従性を優先。

共通構造: 各検査は (name, PASS/FAIL, detail) を返す純粋関数。CLIはそれらを集約し、exit codeを決める。例外は検査内部で捕捉し FAIL に変換する（クラッシュ防止）。

## 実装方針

- 単一ファイル scripts/code_health_check.py に集約。外部依存なし。
- 関数分割: check_conductor_profile / check_hooks / check_agents / check_opencode / check_templates
- CLI: argparseで --verbose, --json, --no-color を提供。任意要件は満たすがデフォルトはテキスト+色付き（端末判定）。
- 色付き: ANSIエスケープ。--no-color または非TTYでは無効化。
- JSON出力: 5検査の詳細を機械可読で出す。
- ロバスト性: 各checkは try/except で囲み、FileNotFound等を FAIL に変換。opencode.json は json.load の例外を捕捉。

## リスクと対策

- パス解決: リポジトリルートを scripts/ の親として解決。cwdに依存しない（Path(__file__).resolve().parents[1]）。
- 文字コード: UTF-8で読む。読込失敗も FAIL 扱い。
- 誤検出: テンプレートのキーワード判定が緩すぎ/厳しすぎ問題。緩めにし、必須3語（成功基準, 軌跡, 自己検証）が1つでも欠ければ FAIL とする。

## トライアングルへの橋渡し

- Yunaへの問い: この5検査の粒度・任意要件の扱いは根本さんのB（違和感・余韻）に照らして適切か。色やJSONは本当に必要か。
- Hayatoへの問い: 深層思考自体が飛躍していないか。5検査の定義に穴はないか。

## 次のアクション

深層思考完了。Yunaに回す。
