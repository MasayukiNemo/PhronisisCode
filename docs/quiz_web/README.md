# Geminiクイズ — リッチWeb UI版 使い方

`scripts/quiz_web.py` は、既存クイズ（`scripts/quiz_game.py`）の出題ロジックを再利用した
グラフィカルなWeb UI版です。出題・難易度4段階・救済（再試行＋有効問のみ）・検証・
quota作法はすべて既存コアをそのまま使います（二重実装なし）。

## まずはこれだけ

- 初めて・見た目を確認したいだけ: `quiz_web_stub.bat` をダブルクリック
  （agy を使わないデモ。quotaを消費せず、サンプル問題で遊べます）
- 本番（Gemini生成）: `quiz_web.bat` をダブルクリック
  （agy 経由で実問を生成します。agyのquotaを消費します）

両方とも、通常はダブルクリックでブラウザが自動で開きます（開かない場合は、黒い画面に
表示されるURLを手動で開いてください）。ウィンドウ（黒い画面）はサーバ本体です。
遊び終わるまで閉じないでください。

## 必要環境

- Windows 10/11
- Python 3（PATHに `py` または `python` があること）
  - Microsoft Store版の `python` スタブは避け、python.org 版を推奨
- 実問生成を使う場合のみ: Antigravity CLI（`agy`）
  - 未導入でも起動・UI表示・`--stub` は使えます。実問生成だけが失敗します

## 起動方法

| 方法 | コマンド / 操作 |
|------|----------------|
| ダブルクリック（本番） | `quiz_web.bat` |
| ダブルクリック（デモ） | `quiz_web_stub.bat` |
| コマンドから | `python scripts/quiz_web.py` |
| 引数付き | `quiz_web.bat --stub` / `quiz_web.bat --no-browser` / `quiz_web.bat --port 8765` |
| exe（ビルド後・本番） | `dist\quiz_web.exe` |
| exe（ビルド後・デモ） | `dist\quiz_web.exe --stub` |

`quiz_web.bat` は `py -3` → `python` の順で実行可能なPythonを探します。
見つからない場合はエラーを表示して閉じずに待機します（黙って落ちません）。

## オプション

| オプション | 説明 |
|-----------|------|
| `--stub` | agyを使わないデモ。サンプル3問（設問数を増やしても最大3問）。quota消費ゼロ。UI確認用 |
| `--no-browser` | ブラウザを自動で開かない。表示されたURLを手動で開く |
| `--port N` | 待受ポートを指定（既定は空きポートを自動選択）。`0`で自動 |
| `--help` | ヘルプ表示 |

## quota の注意（重要）

- 実問生成（`quiz_web.bat` / `--stub` なし）は、開始前に agy の残量を確認します
- 残量が `core.QUOTA_STOP_THRESHOLD`（現在 7%）以下の場合は開始しません
- 残量を取得できない場合は「取得不可」と表示して続行します（取得失敗で止めない）
- ブラウザで開いただけでは消費しません。消費するのは「出題を生成」した時です
- 見学・動作確認は `--stub` を使ってください（消費ゼロ）

## 終了方法

- 画面右上の「終了」ボタン、または
- 黒いコンソールウィンドウで `Ctrl+C`、または
- 黒いコンソールウィンドウを閉じる

ブラウザのタブを閉じただけではサーバは止まりません。終了しないと黒いウィンドウの
プロセスが残り続けるため、上記のいずれかで終了してください。

## 結果の保存

結果画面の「結果を保存」で、出題・回答・正解・解説をテキスト保存します。

- ソース実行時: リポジトリ直下 `quiz_YYYYMMDD_HHMMSS.txt`
- exe実行時: exeと同じフォルダ

保存先のフルパスは保存後に画面に表示されます。
exeは書き込み可能なフォルダ（デスクトップ等）に置いてください。Program Files など
書き込み不可の場所では保存に失敗し、「保存できません」と表示されます。

## exe化（PyInstaller・任意）

配布用の単体exeを作れます。`dist/` `build/` `*.spec` は gitignore 済みで、コミットしません。

### 手順

```
py -3 -m pip install pyinstaller
scripts\build_quiz_web.bat
```

`build_quiz_web.bat` は次と等価です。

```
py -3 -m PyInstaller --noconfirm --onefile --name quiz_web ^
  --paths scripts ^
  --add-data "scripts/quiz_webui;quiz_webui" ^
  scripts\quiz_web.py
```

- `--add-data "scripts/quiz_webui;quiz_webui"`: UIのHTML/CSS/JSを同梱
  （`quiz_web.py` の `resource_dir()` が `_MEIPASS/quiz_webui` から配信）
- `--paths scripts`: `quiz_game.py` / `agy_query.py` のimport解決
- 生成物: `dist\quiz_web.exe`

### console と --windowed について

既存のGUI版（quiz_gui）は `--windowed`（コンソールなし）でexe化していますが、
このWeb版は console あり（既定）を推奨します。理由:

- サーバ起動・ポート・例外などの診断がコンソールに出る（見えないと切り分け不能）
- ブラウザの自動オープンに失敗した場合、コンソールにURLが出るので手動で開ける
- `Ctrl+C` で確実に停止できる（プロセス残留を防ぐ）

`--windowed` にしたい場合の条件: 画面の「終了」ボタンで停止する運用にすること。
自動オープンに失敗するとURLが一切見えないため、`--no-browser` は使わないでください。

### 検証状況

- 起動bat・引数素通し: 検証済み（`--stub --no-browser --port` で起動・API・終了を確認）
- exeビルド: 検証済み（PyInstaller 6.22.3 / Python 3.14 で `scripts\build_quiz_web.bat` を実行）
  - 同梱UIの配信（index.html / style.css / app.js が200）
  - stub動作、および実agyでの1問生成、終了（exit 0）まで確認
- 注意: 起動に使われるPythonは `py -3` 優先のため、`python` と別バージョンの場合があります。
  PyInstallerはビルド時のみの依存で、実行時は不要です

## トラブルシュート

| 症状 | 対処 |
|------|------|
| 「Python 3 was not found」 | python.org版を導入しPATHを通す。Store版スタブは不可 |
| ブラウザが開かない | コンソールのURLを手動で開く。または `--no-browser` で起動 |
| 実問生成が失敗する | agy未導入/未認証の可能性。`--stub` でUI確認、agyを導入して再試行 |
| 「残量取得不可」 | quotaが取れないだけで続行します。実問生成は試行されます |
| ポートが使われている | `quiz_web.bat --port 8765` などで変更 |
| 起動しない/すぐ閉じる | 黒いウィンドウを閉じずにエラー内容を確認。Python/agyを整える |
| 「静的資産が不足しています」と出る | exeの同梱漏れ/破損。`scripts\build_quiz_web.bat` で再ビルド |

## セキュリティ

- localhost（`127.0.0.1`）にのみ待ち受けます（外部公開しません）
- 起動ごとにワンタイムトークンを発行し、Host/Origin検証を行います
- 静的配信は既知の3ファイル（index.html / style.css / app.js）のみ
- 出題文などLLM生成文字列はDOMに `textContent` でのみ描画します（innerHTML不使用）

## 関連ファイル

- `scripts/quiz_web.py` — サーバ本体（薄いHTTPアダプタ）
- `scripts/quiz_webui/` — index.html / style.css / app.js
- `scripts/quiz_game.py` — 出題ロジックの単一正本（変更なしで再利用）
- `quiz_web.bat` / `quiz_web_stub.bat` — 起動バッチ
- `scripts/build_quiz_web.bat` — exeビルド補助
