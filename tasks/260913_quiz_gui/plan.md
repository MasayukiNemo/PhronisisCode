# plan.md — クイズGUI版

## アーキテクチャ

- scripts/quiz_gui.py（新規）。quiz_gameからDIFFICULTY/fetch/require_agy/ask_quota/comment_forをimport
- 画面: 設定→出題→結果の3面。生成はThread、完了をafter(200ms)でポーリング
- ビルド: `--onefile --windowed --name quiz_gui`。成果物dist/quiz_gui.exe（未コミット）

## タスク分解

1. [x] Yuna/Hayato軽量チェック
2. [x] quiz_gui.py実装（＋風情二拍子、Metis指摘反映）
3. [x] ビルド＋exe起動検証（＋flow_test、再ビルド）
4. [x] Hayatoゲート（PASS 4/4）、commit（exe除く）/push

## 依存関係

```
定義チェック → 実装 → ビルド・起動検証 → 確定（クリック完走は根本さん）
```

## リスク

- リスク1: ヘッドレスでクリック検証不可 → 対策: 起動検証までを自己検証とし完走は根本さん確認に切分
- リスク2: windowedでエラー不可視 → 対策: 全エラーを画面ラベルに表示
