# 引き継ぎ書 — BSTBB700Win（Win11環境へ）

## 現状（Phase1済み・2026-09-04）

- Win環境で起動ブロッカーと未配線を修正。py_compile 10件PASS、ロジック単体テスト31/31 PASS、code_health_check 5/5 PASS
- 修正点: app.py直接実行(`python app.py`)可、WH_MOUSE_LL/WH_KEYBOARD_LL実配線(注入無視で再帰防止、横取り/素通し、別スレッドポンプ、縮退起動)、キーボードトリガー配線(横取り消費)、swap/tilt反映、競合警告と反転トグルとcustom VKのUI追加
- Phase1追加: キャプチャ割当(修飾合成・Esc取消)・ビルダー(修飾4+キー82+プリセット15)・一般タブ(自動起動Run・案内・フォルダ・リセット・0.2.0)・Metis重大3件修正+回帰3件
- トレイはMVP簡易版(tkinter常駐)のまま。READMEの看板を簡易版に修正済み

## 構成

```
BSTBB700Win/
  app.py              tkinter設定UI + ルーター
  core/settings.py    JSON保存と排他 logic
  core/mapper.py      XBUTTON/HWHEEL解決（純粋関数）
  core/precise.py     トグル/ホールド状態機械 + SPI写像
  core/keys.py        SendInput計画と実行
  core/hooks.py       フック定数とデコード + HookEngine骨格
  core/discovery.py   ログバッファ
  tests/test_*.py     Mac実行可能な単体テスト5件
  build_win.bat       PyInstaller単一exe化
  README.md           実行と配布手順
```

## Winでの手順

1. `cd BSTBB700Win` し `python app.py` で起動する
2. 設定タブで割り当ては初期無割り当てのため、まずDiscoveryタブ相当のログで実機確認する
3. 進む/戻るを押してXBUTTON1/2の対応を確認する。逆なら `swapBackForward` をJSONでtrueにするかUI拡張する
4. チルトを倒してHWHEELの符号を確認する。逆なら `tiltInverted` をtrueにする
5. 精密は初期チルト左・トグル・25%。中央と進むはホールド可、チルトはトグルのみが仕様
6. `build_win.bat` で `dist\BSTBB700Win.exe` を生成しzip配布する

## Mac版からの教訓（必ず読む）

- delta/Warpで減速しないこと。Winでもフックでdeltaをいじらず、SystemParametersInfoのマウス速度一時変更に一本化した
- 進む/戻るはWinではXBUTTONでdown/upが取れるためホールド可。MacのCtrl+→エミュレーション問題は起きない
- チルトはupがないためトグルのみ。中央はdown/upが取れるためホールド可
- クラッシュ時の低速残留に注意。atexit/signalと起動時復元で二重化済みだが、killや電源断では残るため起動時に強制復元すること（Hayato受入条件）
- SPIはグローバル減速のため、UIに明記し起動中のみ適用すること

## 残課題（Win実機で確認すること）

- Discoveryタブで進む/戻るのXBUTTON1/2対応とチルト符号を確認。逆なら設定画面の入れ替え/反転をON
- 精密のトグル/ホールドとスケール変更が実カーソルに効くこと、終了時に元の速度へ復元されること
- `build_win.bat` で `dist\BSTBB700Win.exe` を生成し配布確認（2026-09-04 Win機で約10MB単一exeのビルド成功。起動確認はこれから。exe本体はgit管理外）
- 自動起動はスタートアップ方式をREADMEに記載済みだが動作未確認
- トレイ本格化(pystray等)とC#化は正式版で検討
- ウイルス対策誤検知とSmartScreenの手順確認
