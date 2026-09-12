# plan.md — クイズゲーム

## アーキテクチャ

- scripts/quiz_game.py（新規、標準ライブラリのみ）。scripts/agy_query.pyをサブプロセスで呼ぶ
- 流れ: quota確認 → テーマ1行 → askでN問JSON取得（失敗時1回リトライ＋部分救済） → 1問ずつ出題・回答（再入力ループ）・正誤 → 解説表示 → スコア＋寸評
- JSON解析失敗時は明示エラー終了（捏造しない）

## タスク分解

1. [x] Yuna/Hayato軽量チェック
2. [x] scripts/quiz_game.py実装
3. [x] 動作検証（パイプ入力で全問回答、スコア確認、失敗パス確認）
4. [x] Metisレビュー、Hayatoゲート（PASS 4/4）、commit/push

## 依存関係

```
定義チェック → 実装 → 検証 → レビュー・確定
```

## リスク

- リスク1: Gemini応答がJSONでない → 対策: strict指示＋```除去＋失敗時明示エラー
- リスク2: cp932で表示クラッシュ → 対策: 安全print（errors=replace）
- リスク3: quota消費 → 対策: 1ゲーム1ask、事前quota確認
