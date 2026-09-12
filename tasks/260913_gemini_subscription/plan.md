# plan.md — 260913_gemini_subscription（Code適応）

## アーキテクチャ

- 配置: scripts/agy_query.py（本家db1a221を最小差分適応。docstring冒頭にCode注記のみ追加、処理本体不変）
- 非変更: 憲章・orchestrationに節を足さない（外部知能化せずツールとして置く）
- 運用: agy-only。ask/quota実測、generateは手順のみ、extract不使用、API自動フォールバックなし
- 記録: knowledge/code_knowledge/agy.md（手順・罠・Code限定）、evolution_logに由来と採否を記録
- task扱い: 採用＋Code流に再構成（brief/deep_thought/plan/log残し、reference/は正本移行後に削除）

## タスク分解

1. [x] scripts/agy_query.py配置と構文確認（syntax-ok、--help、health 5/5）
2. [x] quotaスモーク（gemini_5h 100%で認証確認）
3. [x] askスモーク（一言応答で疎通確認）
4. [x] knowledge/code_knowledge/agy.md作成
5. [x] Daedalus（セキュリティ）/Metis（品質）レビュー
6. [x] reference/削除とevolution_log記録、Hayatoゲート（PASS 4/4）

## 依存関係

```
配置 → quota/askスモーク → 知見記録 → Daedalus/Metis → Hayatoゲート → 確定
```

## リスク

- リスク1: --dangerously-skip-permissionsの読み取り範囲（.env等）→ 対策: Code運用をask/quota中心に限定し、知見に残存リスクとして明記。extract不使用
- リスク2: quota枯渇時の振る舞い → 対策: auto-fallbackなし、7%以下は使わない運用。黙ってAPI課金落ちしない
- リスク3: 本家更新の追従負債 → 対策: 最小差分維持、由来commitをevolution_logに記録、手動cherry-pickのみ
