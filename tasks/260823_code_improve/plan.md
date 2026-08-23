# plan.md — 自己検証昇格 実行計画（Kai が埋める）

## アーキテクチャ

（Kai が記述）

## タスク分解

1. [ ] Hermes相当: 現行 orchestration_flow と hooks の配線確認
2. [ ] 深層思考/Yuna/Hayato: トライアングル
3. [ ] Daedalus: --help em dash 修正 + code_health_check 動作確認
4. [ ] Artemis/Daedalus: orchestration_flow への1行追記
5. [ ] Daedalus: hooks/pre-push への配線追加
6. [ ] Metis/Athena: 統合と品質レビュー

## 依存関係

```
Hermes → 深層思考 → Yuna/Hayato → Daedalus(修正) → orchestration_flow/hooks配線 → 検証 → 再アンカー → Hayato最終ゲート
```

## リスク

- リスク: hooks で health_check が失敗した時に push が BLOCK されて作業が止まる → 対策: WARN に倒すか、失敗時の扱いを明記する
