# plan.md — 1枚HTML文字数カウンタ

## アーキテクチャ

単一HTML（style/script内包、外部link/script srcなし）。
textareaのinputイベントで集計関数を呼びDOM更新のみ。状態なし・保存なし。

集計仕様:
- 改行含む: Array.from(text).length
- 改行含まない: 改行（\r\n|\r|\n）除去後のコードポイント数
- 行数: 空文字→0、あり→改行分割数（\r\n|\r|\n）
- 空白除外: \s 除去後のコードポイント数
- 全角: 非ASCIIコードポイント数、半角: ASCII範囲＋半角カナ（U+FF61-U+FF9Fは半角側に補正）

## タスク分解

1. [ ] index.html 実装（textarea・集計表示・クリアボタン・注記）
2. [ ] 手動検証（7必須項目の目視＋Nodeによる集計ロジック単体確認）
3. [ ] Hayatoゲート＋health check＋commit/push

## 依存関係

```
実装 → 検証 → Hayatoゲート → commit/push
```

## リスク

- 絵文字カウントの直観乖離: Array.fromで1カウントに統一し注記で明示
- CRLF二重カウント: 正規表現で\r\nを1単位として処理
