# BSTBB700Win — Windows 11用トラックボールカスタマイザー

Windows 11 / Python 3.11+ / 標準ライブラリ+ctypesのみ。外部pip不要で実行可。

## 機能（Phase1）

- 5入力（戻る/XBUTTON1、進む/XBUTTON2、中央/MBUTTON、チルト左右/HWHEEL）にキーコンボ割り当て。初期は無割り当てで素通し
- 割当は3経路: キャプチャ（押したキーを取得、修飾同時押し可、Escは取消）・ビルダー（修飾4種+キー一覧+プリセット15種）・クリア
- プリセット15種: 未割り当て・戻るAlt+Left・進むAlt+Right・コピー・ペースト・カット・取り消し・やり直し・全選択・検索・タブ次・タブ前・F13・F14・F15
- 修飾込みをSendInputでグローバル送信
- 精密モード: トグルかホールド択一。トリガーはF13等かマウス（進む/中央/チルト）かcustomKeyから1つ。初期はチルト左・トグル・25%。中央と進むはホールド可、チルトはトグルのみ
- スケール10-100%。SystemParametersInfoのマウス速度を一時変更しOFFで復元
- 一般タブ: 自動起動トグル（凍結exeのみ、レジストリRun）・垂直素通し明記・AV/SmartScreen案内・設定フォルダ・リセット・バージョン
- タスクトレイは簡易常駐（Phase2で本格化）+ tkinter設定 + 精密ON表示 + %APPDATA%/BSTBB700/settings.json保存
- DiscoveryログでXBUTTON/HWHEEL/中央の実機確認

## 実行（Win）

```
cd BSTBB700Win
python app.py
```

## ビルド（Win）

```
build_win.bat
dist\BSTBB700Win.exe
```

## 自動起動

`shell:startup` に `dist\BSTBB700Win.exe` のショートカットを置く。

## 注意

- 精密モードはグローバル減速。全マウスとタッチパッドが減速します
- 初回はSmartScreen警告が出る場合あり。「詳細情報」から実行
- 低レベルフックのためウイルス対策に除外登録が必要な場合あり
- 終了時は自動で元の速度に復元。異常終了時は再起動で復元される
