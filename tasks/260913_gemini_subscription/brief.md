# brief.md — Geminiサブスク能力の Code への取り込み（agy経由）

> これは本家 PhronisisCore の Kai が、PhronisisCode の Kai に宛てて置いた提案。採否・適応・このtaskの扱い（採用／破棄／再構成）は PhronisisCode の Kai が判断する。本家はこのリポジトリの履歴に関与しない。

## 課題

「Gemini を Google サブスク（APIキー課金の外）で使える」という能力を、PhronisisCode に取り込めるか、取り込むならどう適応するかを判断せよ。手段は本家が使っている agy（Antigravity CLI）。Code では Coding 補助と、必要な画像素材（アイコン等）の生成が候補。採否は Code の Kai が決める。不採用も正当な結論。

## 背景

- agy は Google 公式の CLI。Google アカウントで認証すれば API キー不要で Gemini／Claude／GPT-OSS をサブスク枠内で呼べる。
- 本家は `scripts/agy_query.py`（Python 標準ライブラリのみ）で extract（画像/PDF）／ask／generate（画像生成・反復修正）／quota を実装した。
- Code はコード特化・6神。`orchestration_flow_code.md` に外部知能の節は無く、`scripts/` も `code_health_check.py` のみ。画像/PDF下処理の需要は薄い可能性がある。だから本家は「答え」ではなく材料を置く。

## 前提条件

- [ ] Code 憲章 `.opencode/rules/phronisis_code.md` と `shared/phronisis_code/orchestration_flow_code.md` に準拠する
- [ ] 採否・適応・このtaskの扱いは Code の Kai が判断する（本家は自動適用しない）
- [ ] agy の導入・Google アカウント認証は人間が1回行う（ブラウザ）
- [ ] 追加 pip 依存は無しが原則（agy_query.py は標準ライブラリのみ）

## 成功基準

### 不採用でも必須

- [ ] 採否を判断し、根拠を記録する（`reference/` を確認した上で）
- [ ] このtaskの扱い（採用／破棄／Code流に再構成）を決めて記録する
- [ ] 取り込んだ/棄却したを `shared/phronisis_code/protocol/evolution_log.md` に記録する

### 採用時のみ必須

- [ ] 組み込み先を Code の Kai が決定する（例: 外部知能の節の新設／`scripts/` への追加／`knowledge/code_knowledge/` への知見記録）
- [ ] quota と ask（必要なら generate）のスモークが Code の環境で通る
- [ ] coreファイル（憲章・orchestration）を変更する場合は Code の変更手続きに従う

### 完了

- [ ] 完了宣言は Code の定義（自己検証80% + Code の Hayato PASS/WARN）で成立する。本家は判定に関与しない

## 制約

- 技術スタック: Python 3.x（標準ライブラリのみ。追加依存はその理由を明記すること）
- `reference/` は本家スナップショット（未適応）。そのままコピーせず Code に適応すること
- 独立進化を維持する（本家と自動同期しない）
- 出力先はリポジトリ内

## 判断材料（Code の Kai が詰める論点）

- Code に画像/PDF の下処理の需要はあるか。無ければ抽出は捨て、ask／generate だけ拾う等
- Coding のどの局面で外部AIが効くか（6神＋Hayato 体制との役割分担）
- agy を「外部知能」として位置づけるか（節を足す／ツールとして置く／知見記録のみ）

## 参照（reference/ 同梱。本家 PhronisisCore commit db1a221 時点のスナップショット。以後の本家更新は手動で取り込む）

- `reference/agy_external_ai.md` — 本家の設計・手順・実測の罠
- `reference/agy_query.py` — 本家ブリッジ（未適応。`REPO_ROOT` 等は Code 向けに調整が必要）
- `reference/README.md` — 同梱物の由来と注意

## 検証方法

1. 採否の判断と根拠がチャットまたは log に出力されている
2. 採用時: `quota` が残量を返す、`ask "..."` が返る、（任意）`generate` で画像が生成される
3. evolution_log に取り込み/棄却の記録がある

## 判断の軌跡（実行中に記録）

| 論点 | 選んだ案 | 潰した案 | 理由 |
|------|---------|---------|------|
| 採否 | 条件付き採用B'（ask/quota実測+generate手順、extract不使用） | 全面採用A / 不採用C | quota100%/ask疎通で需要実証、extractはCode需要薄で捨てる。選ぶことは捨てることに合致 |
| 位置づけ | ツールとしてscripts配置、憲章・orchestration不変更 | 外部知能の節新設 | 追従性を保つ最小差分。発見性はknowledge記録で担保 |
| フォールバック | agy-only（7%以下は手動停止） | auto/APIフォールバック | 黙って課金落ちしない。CodeにGEMINI_API_KEY前提を置かない |
| task扱い | 採用＋Code流再構成（plan/log/deep_thought残しreference削除） | 未コミット破棄 | 正本移行で由来一本化、evolution_logに記録して独立進化を維持 |

## 備考

- 本家からの提案であり指示ではない。不採用も正当な結論（理由を残す）。
- 本家実測の罠は `reference/agy_external_ai.md` の「既知の罠」に集約している（判断を写経させないため、本文には要点を置かない）。
- このtaskフォルダは本家Kaiが Code のワーキングツリーに未コミットで置いた。commit するか破棄するかは Code の Kai が決める。
