# plan.md — クイズ リッチWeb UI版 配布導線

## アーキテクチャ

```
[ユーザー] ダブルクリック
   └ quiz_web.bat (root, ASCII/CRLF)
        └ py|python scripts\quiz_web.py %*
             └ 既存 quiz_web.py（変更なし。ブラウザ自動起動、127.0.0.1、quota確認）

docs/quiz_web/README.md        起動/オプション/quota/終了/保存/exe手順
scripts/build_quiz_web.bat      PyInstallerビルド補助（未導入時はエラー）
.gitattributes                  *.bat text eol=crlf を追加
```

- コードは変更しない。配布導線（起動・説明・ビルド手順）のみ追加する
- dist/build/*.spec は既存gitignoreのまま（成果物はコミットしない）

## タスク分解

1. [ ] brief / plan 作成
2. [ ] 軽量トライアングル（Yuna / Hayato）
3. [ ] quiz_web.bat（root）
4. [ ] docs/quiz_web/README.md
5. [ ] scripts/build_quiz_web.bat
6. [ ] .gitattributes に新規3バッチ限定で `text eol=crlf`（既存LFバッチは対象外）
7. [ ] bat構文・CRLF・引数素通しの確認（--stub --no-browser を起動→停止）
8. [ ] Metisレビュー（READMEの伝達性）→反映
9. [ ] Hayatoゲート（4点）→ 自己検証 → commit/push

## 依存関係

```
brief → トライアングル → bat/README → 構文・起動確認 → Metis → Hayato → 確定
```

## リスク

- リスク1: batがUTF-8日本語で文字化け → ASCIIのみ＋CRLFで回避
- リスク2: py未導入環境 → pythonへフォールバック、両方無ければ明示エラー＋pause
- リスク3: windowed exeはURL不可視で停止不能 → console推奨をREADMEに明記
- リスク4: PyInstaller未導入で手順未検証 → 未検証と明記。誤った成功を主張しない
- リスク5: .gitattributes変更の副作用 → 既存.batは1件のみ。eol=crlfは新規3ファイル限定にし、既存LFバッチを再正規化しない

<!-- status: complete | agent: kai -->
