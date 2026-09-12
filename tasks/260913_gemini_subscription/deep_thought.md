# deep_thought.md — 260913_gemini_subscription 深層思考

## 構造把握
- Codeはcoding特化・6神プール。orchestrationに外部知能の節なし。scriptsはcode_health_check.pyのみ。
- 本家提案は agy経由でGeminiをサブスク枠で使う能力。extract/ask/generate/quotaの4機能。
- Codeの需要: extract（画像/PDF下処理）は薄い。ask（Coding補助の第二意見）とgenerate（アイコン等素材）は需要あり。
- 現状: agy.exeは当機に存在。認証状態は未確認。knowledgeにdecisions/code_knowledgeが未作成。

## 判断OSへの照合
- 本質的シンプルさ: 4機能まるごとは過剰。拾うものを絞れ。
- 追従性: scripts+知見記録の小規模なら人間が把握可能。orchestration節新設は時期尚早の可能性。
- 思想的一貫性: 独立進化を維持。そのままコピーせずCode向け適応が必須。
- 苦労逃げ: サブスク枠活用はAPI課金逃げとして合致。苦労から逃げる正当な手段。
- 選ぶことは捨てること: extract/multimodal_ingest/MarkItDownは捨てる側。ask/generate/quotaを拾う側。

## 候補案
- A: 全面採用（extract含む本家写経）— Code需要と不一致、機構過剰で却下寄り。
- B: 条件付き採用（ask/generate/quotaのみ、scripts/agy_query.py適応 + knowledge記録、憲章・orchestration不変更）— 本命。
- C: 不採用（理由記録のみ、task破棄）— 需要が実証できない場合の正当解。quota/askの実測が通らない場合に転落。
- D: 知見記録のみ（コード置かず、手順だけ残す）— agy未認証・規約懸念が残る場合の中間解。

## 確信度
- Bに65%。quota実測とYuna/Hayatoの検証で70%超えを狙う。70%未満のためフルで回す。

## 再アンカー問い
- この取り込みはbriefの成功基準（採否判断+evolution_log記録）に忠実か。大局観（Codeの軽さを保つ）を見失っていないか。
