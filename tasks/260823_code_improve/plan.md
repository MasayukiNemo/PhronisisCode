# plan.md — 自己検証昇格 実行計画

## アーキテクチャ

```
shared/phronisis_code/orchestration_flow_code.md
  └─ Hayatoゲート節に1-2行追記: `python scripts/code_health_check.py --no-color` が exit 0 を必須化

hooks/pre-push
  └─ handover_check 後に health_check 呼び出しを追加（python_run.sh経由、BLOCK明記）

scripts/code_health_check.py
  └─ em dashは b18b998 で - に置換済み。再検証のみ（--help が cp932で通ること）
```

- 各変更は既存パターンを踏襲。orchestration_flowは1-2行、hooksは bash/python_run.sh 経由。
- health_checkは5検査で軽量、push時の追加コストは小。

## トライアングル結果サマリ

- 深層思考: 自己参照の閉じ方としてhealth_checkを機械ゲートに昇格。配線先と失敗時の扱いを分岐点として抽出。
- Yunaプリズム照合:
  - 指摘: pre-push(WARN)は摩擦小だが見逃しを生む。根本さんのBは「止めるべき時は止める」を好む可能性。→ 採用: BLOCKを選ぶことで思想的一貫性（Honest）と handover_checkとの整合を優先。
  - 指摘: em dash置換は既に実証済み、エンコーディング対策は過剰。→ 採用: 置換を維持。
  - 申告: 駆動試験のplan.md残課題に触れるとスコープ肥大。→ 採用: 本タスクでは触れない（brief制約遵守）。
- Hayato刺突:
  - 「pre-pushでWARNならhealth_checkがFAILでもpushが通る。宣言と実体の乖離が残る」→ 対応: BLOCKに倒し、失敗時は exit 1。
  - 「health_checkがスクリプト欠落でクラッシュしたらhooks全体が落ちる」→ 対応: スクリプト存在チェックとpython_run.sh経由で存在しない場合もexit 1でBLOCK。
  - 「orchestration_flow追記が冗長だと追従性が落ちる」→ 対応: 1-2行に抑える。
- 中間Hayato軽量チェック（5行以内）: 仕様逸脱なし。手続き揃い。致命傷対策あり。→ PASS。次へ進め。

## タスク分解

1. [x] Hermes相当: 現行 orchestration_flow と hooks の配線確認（readで実施）
2. [x] 深層思考/Yuna/Hayato: トライアングル完了、deep_thought.md 出力
3. [x] Daedalus: --help em dash 再検証（b18b998で置換済み、--help exit0確認）
4. [x] Daedalus+M: orchestration_flow への1行追記（Hayatoゲート必須化: --no-color exit0必須/BLOCK）
5. [x] Daedalus: hooks/pre-push への配線追加（BLOCK明記: pre-pushでhealth_check呼び出し）
6. [x] Metis/Athena: 統合と品質レビュー、自己検証、再アンカー、Hayato最終ゲート

## 依存関係

```
Hermes → 深層思考 → Yuna/Hayato → Daedalus(再検証) → orchestration_flow/hooks配線 → 検証 → 再アンカー → Hayato最終ゲート
```

クリティカルパス: hooks配線 → 検証。見積: 実装15分、検証15分。ボトルネックはhooksのbash互換性。

## リスク

- リスク: hooksでhealth_checkが失敗した時にpushがBLOCKされて作業が止まる → 対策: BLOCKを明記し、失敗時のメッセージで原因（health_check）を明示。誤検知は5検査が軽量で少ない。
- リスク: Windowsでbash経由のパス解決が壊れる → 対策: PROJECT_DIR/scripts/code_health_check.py で絶対パス指定、python_run.sh経由。

## 招集判断詳細

| 神 | 判定 | 理由 |
|----|------|------|
| Gaia | 呼ばない | 設計2案は深層思考で収束、アーキテクチャ分岐なし |
| Hermes | 呼ぶ（Kai代行） | orchestration_flow/hooksの事実確認が必要 |
| Artemis | 呼ばない | 変更2ファイルで依存単純 |
| Daedalus | 呼ぶ（Kai代行） | --help修正とhooks実装が核 |
| Metis | 呼ぶ（Kai代行） | 実装を伴うタスクは原則招集 |
| Athena | 呼ぶ（Kai代行） | 複数視点の統合が必要 |

## L2.5 自律実行宣言

推論で進めてみる。実行済み時制で実装まで行う。24時間以内の差し戻し可。
