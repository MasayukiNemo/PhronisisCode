# brief.md — クイズ リッチWeb UI版の配布導線（起動bat・README・exe手順）

## 課題

前タスク 261006_quiz_rich の成果（scripts/quiz_web.py）に、Windowsでダブルクリック起動できる
バッチと使い方READMEを追加する。既存quiz_guiのexe作法（PyInstaller・distはgitignore・windowed等）に
沿ったexe化も検討し、可能な範囲で手順をREADMEに含める。

## 前提条件

- [ ] 起動コマンドは `python scripts/quiz_web.py` を呼ぶ（ロジック変更なし）
- [ ] dist/ build/ *.spec はgitignore済み（成果物はコミットしない）
- [ ] quota作法・セキュリティは前タスクのまま（本タスクで触らない）
- [ ] .bat は文字化け回避のためASCIIのみ、CRLF、`%~dp0`基準で動く

## 成功基準

- [ ] 必須: `quiz_web.bat`（リポジトリ直下）をダブルクリックすると `python scripts/quiz_web.py` が起動する
- [ ] 必須: python/py が見つからない場合はエラーを表示して終了する（黙って閉じない）
- [ ] 必須: `quiz_web.bat --stub` のように引数を素通しできる（%*）
- [ ] 必須: README（docs/quiz_web/README.md）に起動方法・`--stub`/`--no-browser`/`--port`・quota注意・終了方法・結果保存先を記載
- [ ] 必須: EXE化手順（PyInstaller・`--add-data`・console推奨とwindowedの注意・dist非コミット）をREADMEに記載
- [x] 任意: ビルド補助バッチ scripts/build_quiz_web.bat を用意
- [x] 任意: exe実ビルドとsmoke（PyInstaller導入の上で実施。同梱UI配信・stub・実agy1問・終了を確認）

## 制約

- コード（quiz_web.py / quiz_webui）の挙動は変更しない（配布導線のみ追加）
- ドキュメントはUTF-8。batはASCII＋CRLF（cmd のLF問題回避）。.gitattributes に新規3ファイル限定で `text eol=crlf` を追加（既存LFバッチは対象外）
- 成果物はリポジトリ内。dist/build/*.specはコミットしない

## 判断の軌跡（実行中に記録）

| 論点 | 選んだ案 | 潰した案 | 理由 |
|------|---------|---------|------|
| 起動batの配置 | リポジトリ直下 quiz_web.bat | scripts/配下 | ダブルクリック動線。`python scripts/quiz_web.py` の相対が直下で一致 |
| batの中身 | ASCII＋CRLF、py→pythonフォールバック | 日本語メッセージ | cmdのcp932/UTF-8とLF問題で文字化け・誤動作を避ける |
| 引数 | %* 素通し | 固定起動 | --stub/--no-browser/--port をユーザーが選べる |
| README配置 | docs/quiz_web/README.md | scripts直下/ルート | ルートREADMEは既存。docs/tetris の前例に合わせる |
| exe方式 | console（--onefile）推奨 | quiz_gui同様の--windowed | サーバはURL表示とCtrl+C終了が要る。windowedはURL不可視・停止不能になる。差異理由をREADMEに明記 |
| exe実ビルド | PyInstallerを導入して実ビルド・smoke・実agy1問まで検証 | 手順のみで未検証のまま | 可能だった。exe同梱UI・agy同梱・終了まで確認できた方が誠実（Hayatoの「検討の体を成していない」を解消） |
| ビルド補助 | scripts/build_quiz_web.bat | README本文のみ | 手順を再現可能な形で固定。未導入時はエラーで止まる |
| .gitattributes | 新規3バッチ限定で `text eol=crlf` | `*.bat` 一括指定 | `*.bat` は既存LFバッチ（build_win.bat）を再正規化して差分を混ぜる。新規ファイル限定で影響を閉じる |

<!-- status: complete | agent: kai -->
