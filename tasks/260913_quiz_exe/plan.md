# plan.md — クイズexe化

## アーキテクチャ

- quiz_game.py改修: agy呼出をsubprocessからimport agy_queryに切替（凍結対応）、起動時メニュー（テーマ・設問数・難易度）、難易度別プロンプト
- ビルド: PYTHONPATH=scriptsで `python -m PyInstaller --onefile --noconsole?` → いや対話式なのでコンソール必須。`--onefile --name quiz_game scripts/quiz_game.py`
- 成果物: dist/quiz_game.exe（未コミット）

## タスク分解

1. [x] Yuna/Hayato軽量チェック
2. [x] quiz_game.py改修＋スクリプト動作検証
3. [x] PyInstallerビルド＋exe動作検証（再ビルド含む）
4. [x] Metis/Hayato（WARN、書面解消）、commit（exe除く）/push

## 依存関係

```
定義チェック → 改修 → ビルド → 検証・確定
```

## リスク

- リスク1: frozen時REPO_ROOT崩れ → 対策: import取込、cwdはexe親に
- リスク2: ビルドサイズ・起動時間 → 対策: 標準libのみで最小構成
- リスク3: exeからのagy認証（%USERPROFILE%/.gemini参照） → 対策: 実実行で検証
