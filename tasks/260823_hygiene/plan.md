# plan.md — Hygiene 実行計画

## アーキテクチャ

```
git remote
  └─ 平文化: https://github.com/MasayukiNemo/PhronisisCode.git（token除去、credential helperに委譲）

shared/phronisis_code/protocol/evolution_log.md
  └─ v1.0-fix2 追記: a14806c(health_check昇格)+b18b998(em dash)+hygiene 3点を要約

shared/phronisis_code/orchestration_flow_code.md
  └─ Hayatoゲート節末尾に3ゲート表追記（pre-commit/pre-push handover/pre-push health、タイミング/BLOCK明記）
```

- いずれも1-3行の追記で完結。外部依存なし。

## トライアングル結果サマリ

- 深層思考: 衛生対策は逃げ切れない苦労と位置付け、token/evolution/可視化の3点を分岐点として抽出。
- Yunaプリズム照合:
  - 指摘: token除去は Honest に忠実だが次回pushで認証摩擦が生じる。→ 採用: それでも書き換えを選び、revoke要をlogに明記。根本さんの「苦労は逃げろ」は今回の苦労には適用しない。
  - 指摘: evolution_logは要約でよい。詳細はgit logで追える。→ 採用: 要約1エントリ。
  - 申告: 3ゲート表は別章にすると概念が増える。→ 採用: Hayatoゲート節末尾に3行で収める。
- Hayato刺突:
  - 「tokenはremoteだけでなく過去のログや履歴にも残る。除去だけで済むと思うな」→ 対応: 除去に加えrevoke要をlogに明記。
  - 「3ゲート表が将来のhook変更と乖離したら嘘になる」→ 対応: 表は現行3ゲートの責務分担のみに留め、詳細はコードを見に行く形で追従性を維持。
  - 「evolution_logが要約すぎて何をしたか分からない」→ 対応: コミットhash(a14806c/b18b998)を含め追跡可能に。
- 中間Hayato軽量チェック（5行以内）: 仕様逸脱なし。手続き揃い。致命傷対策あり。→ PASS。次へ進め。

## タスク分解

1. [x] Hermes: 現行 remote/evolution_log/orchestration_flow の事実確認（read/bashで実施）
2. [x] 深層思考/Yuna/Hayato: トライアングル完了、deep_thought.md 出力
3. [x] Daedalus: git remote 正規化（平文化）
4. [x] Daedalus+M: evolution_log 追記（v1.0-fix2）
5. [x] Daedalus+M: orchestration_flow 3ゲート表追記（Hayatoゲート節末尾）

## 依存関係

```
Hermes → 深層思考 → Yuna/Hayato → Daedalus(remote) → evolution_log → orchestration_flow → 検証 → 再アンカー → Hayato最終ゲート
```

## リスク

- リスク: token除去後に push が認証失敗する → 対策: credential helper への委譲を確認し、失敗時は手動で gh auth login を促す
