# BSTBB700Win — Windows 11用トラックボールカスタマイザー

Windows 11 / Python 3.11+ / 標準ライブラリ+ctypesのみ。外部pip不要で実行可。

## 機能

- 5入力（戻る/XBUTTON1、進む/XBUTTON2、中央/MBUTTON、チルト左右/HWHEEL）にキーコンボ割り当て。初期は無割り当てで素通し
- 修飾込みをSendInputでグローバル送信
- 精密モード: トグルかホールド択一。トリガーはF13等かマウス（進む/中央/チルト）から1つ。初期はチルト左・トグル・25%。中央と進むはホールド可、チルトはトグルのみ
- スケール10-100%。SystemParametersInfoのマウス速度を一時変更しOFFで復元
- タスクトレイ簡易常駐 + tkinter設定 + 精密ON表示 + %APPDATA%/BSTBB700/settings.json保存
  - トレイはMVP簡易版でtkinterメインウィンドウ常駐。正式版でpystray等に拡張予定
- DiscoveryログでXBUTTON/HWHEEL/中央の実機確認
- 低レベルフックはWH_MOUSE_LL/WH_KEYBOARD_LL実配線。SendInput由来の注入イベントは無視し再帰を防止。割り当て時は横取り(嚥下)、未割り当ては素通し
- キーボードトリガー(F13/F14/F15/CapsLock/custom)は横取り消費。精密と排他中のマウスボタン割り当ては設定画面に警告表示

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
