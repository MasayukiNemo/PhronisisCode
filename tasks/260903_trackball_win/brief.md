# brief.md — タスク定義

## 課題

Windows 11でBluetooth接続の5ボタントラックボールBSTBB700（チルト対応高速慣性ホイール）の進む/戻る、チルト左右、ホイール中央押し込みをキーカスタマイズできる常駐アプリを作る。Mac版で確立した精密モード（カーソル一時減速）をWindowsでも提供する。

## 前提条件

- [x] 対象デバイス: BUFFALO BSTBB700。Bluetooth接続、5ボタン+チルト対応高速慣性ホイール。1台専用でMVP
- [x] Windows 11 64bit、Python 3.11+（標準ライブラリ+ctypesのみ、pip不要で実行可）
- [x] Windowsでは進む/戻るがXBUTTON1/XBUTTON2としてそのまま返るため、down/upで押しっぱなし判定が可能（MacのCtrl+→エミュレーション問題は起きない）
- [x] 実装環境はMac（ビルド不可）のため、Win環境への引き継ぎを前提とする。Mac側では構文チェックとロジック単体テストで検証する
- [x] Mac版の知見を継承: delta/Warp方式は使わず、システムのポインタ速度一時変更に一本化する

## 成功基準

- [ ] 必須1: 進む / 戻る / チルト左 / チルト右 / 中央押し込み の5入力それぞれに任意のキーコンボ（例 Ctrl+C, Ctrl+Shift+T, F13等）を割り当て可能
- [ ] 必須2: 修飾キー（Ctrl/Shift/Alt/Win）+任意キーのエミュレーションがグローバルに動作（SendInput）
- [ ] 必須3: 精密モード — トグルかホールドを選択可能。トリガーは未使用キー（F13等）またはマウス側（進む/中央/チルト）から1つ。進む/中央はホールド可、チルトはトグルのみ（upなしのため）。割り当てと排他
- [ ] 必須4: 精密スケールをUIで変更可能（10%〜100%、デフォルト25%）。SystemParametersInfoのマウス速度を一時変更し、OFFで復元する
- [ ] 必須5: 設定UI（タスクトレイ常駐 + 設定ウィンドウ、精密ON表示）で各割り当てと精密設定を変更・保存・再起動後も保持（%APPDATA%/BSTBB700/settings.json）
- [ ] 必須6: DiscoveryログモードでXBUTTON/HWHEEL/中央ボタンのどれで届くかを判別できること
- [ ] 任意1: 自動起動（スタートアップ登録）、プロファイル切替
- [ ] 任意2: 垂直ホイール素通し、水平チルトのみカスタムの明記

## 制約

- 技術スタック: Python 3.11+標準ライブラリ+ctypesのみ（Win32 API直呼び）。外部pip不要。配布はPyInstallerで単一exe化（Win環境でビルド）
- 期限: 未定（MVP検証 → 段階拡張）
- 参照: Mac版 tasks/260829_trackball/tech_guide_precise_mode_macos.md、LinearMouseのHID加速方式、MSDN SendInput/SystemParametersInfo/Raw Input
- 配布: zip直配布。署名なしMVP。自動起動はスタートアップフォルダ方式
- UI: タスクトレイ常駐 + tkinter設定ウィンドウ + 精密ON表示

## 判断の軌跡（実行中に記録）

| 論点 | 選んだ案 | 潰した案 | 理由 |
|------|---------|---------|------|
| 言語 | Python+ctypes標準のみ | C#/.NET WPF | Mac側にSDKがなく検証不能。PythonならMacで構文とロジックを検証しWinでそのまま実行とPyInstaller化ができる |
| イベント取得 | WH_MOUSE_LL + WH_KEYBOARD_LL低レベルフック | Raw Inputのみ/ドライバ | フックはctypesだけで実装でき、XBUTTON/HWHEEL/中央を横取りできる。Raw Inputは将来のデバイス限定化で追加 |
| キー送信 | SendInput | keybd_event旧API | SendInputが公式で修飾込みの確実な送信ができる |
| 精密減速 | SystemParametersInfo SPI_SETMOUSESPEED一時変更 | deltaスケール/Warp | Mac版でdelta無視とWarp逆走が確定したため。Winでもシステム速度変更が確実で方向を触らない |
| 精密トリガー | 単一選択+トグル/ホールド択一、中央と進むはホールド可、チルトはトグルのみ | 全ボタンでホールド可 | チルトはupイベントがないためホールド不可。WinではXBUTTONでdown/upが取れるため進む/中央はホールド可としMacの制約を緩和 |
| 設定保存 | %APPDATA%/BSTBB700/settings.json | レジストリ | JSONは人間可読でMac版UserDefaultsと対応し引き継ぎが容易 |
| UI拡充Phase1技術 | Python+tkinter継続・段階的全部盛り | C#作り直し | Win機で検証継続が勝つ。配布性のみでは作り直しのコストに見合わない |
| Phase1範囲 | 操作系(キャプチャ+ビルダー+プリセット+一般タブ) | 全部盛り一気 | 毎日触る割当の痛みから。常駐系(HUD/トレイ/自動起動/列挙)はPhase2 |
| 自動起動方式 | レジストリRunキー(winreg標準のみ) | スタートアップlnk | lnkはCOM実装が重い。Runキーは標準のみでトグル可 |
| Win不要置換 | 権限ガイド→AV/SmartScreen案内、反転系は対象外 | Macのまま移植 | SPIは方向を触らない。実機反転報告が出たらHID相当で対応 |
| Phase2範囲 | HUD+トレイ+安全装置を搭載、6列挙・7可視化は不要 | 全部盛り | 6はVID特定済み前提で不要、7は手触り確認済みで不要。8はPhase1済み |
| トレイ方式 | ctypes Shell_NotifyIconW自前実装 | pystray導入 | 標準のみ方針を維持。失敗時は窓常駐に縮退 |
| HUD方式 | tkinter pillのflash表示+自動消去 | 常時表示 | フック別スレッドからはafter(0)でUIスレッドに寄せる |
| 安全装置Win化 | Esc5連打+%TEMP%旗・debug log・チルト0.3s・タッチ由来素通し | Macのまま | タッチ判別はdwExtraInfoのFROMTOUCH署名で素通し |
