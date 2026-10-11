# plan.md — 実装計画

## アーキテクチャ

単一HTML（tools/zenkaku-hankaku.html）。構成は style（head内）+ body（入力textarea / ボタン群 / 出力textarea+プレビュー）+ script（head末尾・body末）。外部依存なし。

変換ロジック:
- 英数記号: U+FF01–U+FF5E ⇔ U+0021–U+007E のコードポイント加減算（±0xFEE0）
- スペース: U+3000 ⇔ U+0020
- カタカナ全→半: 全角カタカナ→半角対応表（ァ～ヶ・濁点結合対応）
- カタカナ半→全: 半角カタカナ→全角対応表（ｶﾞ等の結合2文字→ガに合成）

## タスク分解

1. [ ] HTML雛形＋変換ロジック実装
2. [ ] 手動検証（8必須項目の確認）
3. [ ] code_health_check + utf8確認、Hayatoゲート、commit/push

## 依存関係

```
タスク1 → タスク2 → タスク3
```

## リスク

- カタカナ濁点の合成漏れ: 対応表を全網羅し検証で確認
- XSS: innerHTMLを使わず textContent/value のみで表示
