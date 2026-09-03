# 引き継ぎ書 — BSTBB700Win（Win11環境へ）

## 現状

- Mac側で実装と検証まで完了。py_compile 7件PASS、ロジック単体テスト13/13 PASS、code_health_check 5/5 PASS
- Win実機でのフック確認は未実施のため、Win環境でDiscoveryから着手すること
- Hayato中間はWARN（受入条件付き着手可）、Metis指摘3件は修正済み。最終ゲートはこれから回す

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

## 残課題

- HookEngine.startのSetWindowsHookEx実配線は骨格のみ。Win環境で実機フックを実装しDiscoveryと接続する
- トレイ常駐はtkinter常駐の簡易版。正式版ではpystrayかC#化を検討する（Hayato条件）
- 自動起動はスタートアップ方式をREADMEに記載済みだが動作未確認
- ウイルス対策誤検知とSmartScreenの手順確認
