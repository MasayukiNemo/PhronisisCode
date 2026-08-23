# plan.md — 駆動試験 実行計画

## アーキテクチャ

単一ファイル `scripts/code_health_check.py` に集約。外部依存なし、Python標準のみ。

```
scripts/code_health_check.py
  ├─ resolve_root()             # scripts/ の親を repo root として解決（cwd非依存）
  ├─ check_conductor_profile()  # 1. knowledge/conductor_profile_lite.md 存在 + 非空 + 見出し含む
  ├─ check_hooks()              # 2. hooks配下6ファイル存在
  ├─ check_agents()             # 3. 6神 profile.md 存在
  ├─ check_opencode()           # 4. opencode.json valid + 8 agents
  ├─ check_templates()          # 5. tasks/_template/brief.md, log.md に必須フィールド
  ├─ run_all_checks()           # 例外を捕捉し FAIL に変換（クラッシュ防止）
  └─ CLI (argparse)             # --verbose / --json / --no-color、PASS緑/FAIL赤、exit code
```

- 各 check は (name, passed: bool, detail: str) を返す純粋関数。
- CLIは結果を集約し、一覧表示 + サマリ + exit 0/1 を決定。
- 色付きは ANSI。TTY判定と --no-color で無効化。
- JSON出力は --json で機械可読（checks配列 + summary）。

## トライアングル結果サマリ

- 深層思考: 5検査の共通構造を抽出、ロバスト性と追従性を両立する設計に収束。
- Yunaプリズム照合:
  - 指摘: 「参照破損がないこと」の定義が曖昧。厳格すぎると誤FAIL。→ 採用: 存在+非空+見出し含むの3段階で緩めに判定。Yuna B-Side「厳格な破損検出（リンク切れ追跡）案は捨てた。追従性優先でシンプルに」。
  - 指摘: 任意要件（--verbose/--json/色）は削るな。根本さんは「端折り」を嫌う。→ 採用: 両立案。デフォルトはテキスト+色、フラグで verbose/json。
  - 申告: 6神全招集は過剰。思想的一貫性（本質的シンプルさ）に反する。→ 採用: Hermes/Daedalus/Metis/Athenaのみ実質招集、Gaia/Artemisは呼ばない理由を明記。
- Hayato刺突:
  - 「5検査で1つでも例外投げたら全体クラッシュする穴」→ 対応: 各checkをtry/exceptで包む。
  - 「cwd依存で別ディレクトリから実行したらパス解決失敗」→ 対応: __file__ 基準でroot解決。
  - 「exit code 仕様を守らないとCIで使えない」→ 対応: 1つでもFAILなら exit 1。
- 中間Hayato軽量チェック（5行以内）: 仕様逸脱なし。手続き（brief/plan/log/軌跡）揃い。致命傷対策あり。→ PASS。次へ進め。

## タスク分解

1. [x] Hermes相当: 既存ファイル構造の調査（Kaiが代行、bash/readで実施済み）
2. [x] 深層思考/Yuna/Hayato: トライアングル完了、deep_thought.md 出力
3. [x] Daedalus: scripts/code_health_check.py 実装
4. [x] Metis: 品質レビュー（可読性・保守性）- 実装後にKaiがセルフレビュー
5. [x] Athena: 5検査の統合とCLI出力整形 - Daedalusと同時
6. [x] 自己検証80% + Hayatoゲート + 再アンカー（2ループ目）

## 依存関係

```
Hermes → 深層思考 → Yuna/Hayato → Daedalus/Metis/Athena（同一ファイル内で統合） → 自己検証 → 再アンカー → Hayato最終ゲート
```

クリティカルパス: 実装 → 自己検証。見積: 実装30分、検証15分。ボトルネックは例外時のFAIL変換の網羅性。

## リスク

- リスク: 既存 hooks との整合性崩し → 対策: 既存ファイルを直接編集しない。新規は scripts/ のみ。
- リスク: テンプレートのキーワード判定が環境で揺れる → 対策: キーワードは部分一致で緩めに判定。
- リスク: opencode.json の agent数カウントが将来変動 → 対策: 期待8と実測を両方表示し、差分をdetailに出す。

## 招集判断詳細

| 神 | 判定 | 理由 |
|----|------|------|
| Gaia | 呼ばない | 設計2案なし。単一スクリプトでアーキテクチャ分岐なし |
| Hermes | 呼ぶ（Kai代行） | 事実確認が必要。既に調査済み |
| Artemis | 呼ばない | 3ファイル以上変更なし、依存単純 |
| Daedalus | 呼ぶ（Kai代行） | 実装・バグ検出が核 |
| Metis | 呼ぶ（Kai代行） | 実装タスクは原則招集 |
| Athena | 呼ぶ（Kai代行） | 複数視点の統合が必要 |

## L2.5 自律実行宣言

推論で進めてみる。実行済み時制で実装まで行う。24時間以内の差し戻し可。
