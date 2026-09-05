# plan.md — 実装計画

## アーキテクチャ

```
[Bluetooth BSTBB700] --HID--> [Windows] --WH_MOUSE_LL/WH_KEYBOARD_LL--> [BSTBB700Win app.py]
                                                                              |
                                   +--------------------------+-----------------+
                                   |                          |                 |
                            [Discovery]                [Hook Engine]      [Settings Store]
                            ログ表示                   XBUTTON/HWHEEL      %APPDATA% JSON
                            XBUTTON/HWHEEL/            MBUTTON/keyDown     mappings+precise
                            中央/keyCode               横取り/素通し
                                   |                          |
                                   +------------+-------------+
                                                |
                                         [Event Router]
                                         - XBUTTON1->back, XBUTTON2->forward
                                         - HWHEEL->tiltLeft/Right
                                         - MBUTTON->center
                                         - 精密トリガー判定(トグル/ホールド択一)
                                                |
                                 +--------------+--------------+
                                 |                             |
                          [Mapping Store]               [Precise Engine]
                          ButtonID->KeyCombo            SPI_GETMOUSESPEED保存
                          JSON Codable                  SPI_SETMOUSESPEEDにscale反映
                          排他バリデーション            OFFで復元、atexit/signal二重復元
                                 |                             |
                                 +--------------+--------------+
                                                |
                                          [Key Emitter]
                                          SendInputで修飾+キー送信
                                                |
                                          [UI Layer]
                                          タスクトレイ + tkinter設定 + 精密ON表示
                                          + スタートアップ登録 + JSON永続化
```

技術選定:
- 言語: Python 3.11+、標準ライブラリ+ctypesのみ。tkinterは標準同梱。外部pip不要でWin実行可
- 取得: WH_MOUSE_LL（XBUTTON/HWHEEL/MBUTTON横取り）+ WH_KEYBOARD_LL（F13等トリガー）。ctypesでSetWindowsHookEx直呼び
- 送信: SendInput（KEYBDINPUT、修飾はwVk+wScan併用）。旧keybd_eventは不採用
- 減速: SystemParametersInfoW(SPI_GETMOUSESPEED/SPI_SETMOUSESPEED)。scale 0.10-1.0を速度1-20に写像。保存と復元をatexit/signalで二重化
- 保存: %APPDATA%/BSTBB700/settings.json。mappings+preciseEnabled/Trigger/Mode/Scale+discoveryEnabled
- 常駐: タスクトレイ（pystrayなしのctypes最小実装かtkinter常駐。MVPはtkinterメイン+トレイ簡易）。自動起動はスタートアップフォルダのショートカット
- 配布: Win環境で PyInstaller --onefile --windowed で単一exe化。zip直配布

トレードオフ:
- C#ネイティブ化で性能と配布性は上がるが、Mac側検証が不能になるためMVPはPythonで先行し、正式版でC#化の余地を残す
- Raw Inputでデバイス限定化できるがMVPはグローバル減速でUI明記し将来拡張に退避（Mac版briefと同一判断）
- チルトはHWHEELでupがないためホールド不可でトグルのみ。進む/中央はXBUTTON/MBUTTONでdown/upが取れるためホールド可（Macの制約をWinで緩和）

## タスク分解

1. [ ] T1 core/settings.py: JSON読み書き、デフォルト（mappings空、precise有効・チルト左・トグル・25%）、排他バリデーション
2. [ ] T2 core/mapper.py: ButtonID定義、KeyCombo定義、VK表、割り当て解決と横取り/素通し判定
3. [ ] T3 core/precise.py: トグル/ホールド状態機械、スケール写像（0.10-1.0→1-20）、SPI保存と復元、atexit/signal
4. [ ] T4 core/keys.py: SendInputラッパ（ctypes、Windows以外ではImportErrorで無効化しテスト可能に）
5. [ ] T5 core/hooks.py: WH_MOUSE_LL/WH_KEYBOARD_LLフック骨格（Windows以外ではダミー化）、Discoveryコールバック
6. [ ] T6 core/discovery.py: イベントログ蓄積と表示用整形
7. [ ] T7 app.py: tkinter設定UI（5行割り当て+精密+Discovery+一般）+トレイ常駐+起動時復元
8. [ ] T8 tests: Macで実行可能な単体テスト（settings/mapper/preciseのロジック、ctypes部分はモック）
9. [ ] T9 build_win.bat + requirements.txt + README.md + handover_win.md: Win引き継ぎ一式
10. [ ] T10 検証: Macでpytest相当実行とpy_compile、Hayatoゲート、コミット

## 依存関係

```
T1 -> T2 -> T5 -> T7
T1 -> T3 -> T7
T4 -> T5
T6 -> T7
T1-T4 -> T8 -> T10
T7 -> T9 -> T10
```

MVPクリティカルパス: T1-T2-T3-T4-T7-T8 で最小動作。T5フック実機確認とT6 DiscoveryはWin環境で実施

## リスク

- R1 XBUTTONのID決め打ち（1=戻る/2=進む）がBSTBB700で逆の可能性 → 対策: Discoveryログで実機確認、tiltInverted相当の反転設定を残す
- R2 SPI_SETMOUSESPEEDが全デバイス巻き込み → 対策: UIにグローバル明記、将来Raw Input限定に拡張
- R3 クラッシュ時に低速残留 → 対策: 保存値の二重復元（atexit/signal/起動時）、起動時に前回異常終了を検出したらデフォルトに戻す
- R4 ウイルス対策誤検知（フック+SendInput） → 対策: READMEに除外手順、SmartScreen回避手順を明記
- R5 Mac側でWin32実行不能 → 対策: プラットフォーム分岐でimportを遅延し、ロジックは純粋関数でテスト可能にする

## 招集判断の記録

- Hermes: 招集予定。SendInput/SystemParametersInfo/WH_MOUSE_LLの仕様検証を依頼
- Gaia: 未招集。設計案分岐がなくPython+ctypesに一意のため。呼ばなかった理由: 創発の種不足なし
- Artemis: 本planで代替。ファイル数は10程度だが仕様確定済みのため計画のみ
- Daedalus: 実装フェーズで招集。T1-T9の実装を担当
- Metis: 実装後の品質レビューでHayatoゲート前に指摘
- Athena: 未招集。統合はKaiが担う
- Yuna/Hayato: トライアングルで回す。Hayato中間軽量チェックを次に実施

## Phase1 リッチ化計画（操作系4点・2026-09-04合意）

背景: Mac版読解で差分9点を確定。Phase1は毎日触る操作系(キャプチャ+ビルダー+プリセット+一般タブ)を先行。常駐系(HUD/トレイ/自動起動実装/デバイス列挙)はPhase2、安全・可視化はPhase3。

タスク分解:

1. [ ] P1-1 core/vktable.py: VK一覧表(英数/F1-F24/方向/編集系/修飾表示)とWinプリセット14種(未割り当て・戻るAlt+Left・進むAlt+Right・コピー・ペースト・カット・取り消し・やり直し・全選択・検索・タブ次・タブ前・F13・F14・F15)。純粋データでMacテスト可
2. [ ] P1-2 core/autostart.py: レジストリRunキー(HKCU...Run/BSTBB700Win)で自動起動トグル。winreg遅延importでMacではno-op。exeパス解決はsys.executable凍結時とscript時を区別
3. [ ] P1-3 app.py割当タブ: 各行をキャプチャボタン+ビルダー開閉に作り替え。キャプチャはモーダルダイアログで次キー横取り取得(Esc取消)、修飾はGetKeyState系で同時取得。ビルダーは修飾4チェック+キー選択+プリセット+反映/クリア
4. [ ] P1-4 app.py一般タブ新設: 自動起動トグル・垂直素通し明記・AV/SmartScreen案内・設定フォルダを開く・設定リセット・バージョン表示
5. [ ] P1-5 tests/test_phase1.py: プリセットVKが一覧表に存在すること、キャプチャ純粋部の判定、autostartのMac no-op、ビルダー往復
6. [ ] P1-6 検証: py_compile全件、17+新規PASS、code_health_check 5/5、README/handover/log更新、Hayato最終ゲート

依存: P1-1 -> P1-3 -> P1-5 -> P1-6、P1-2 -> P1-4 -> P1-5

リスク:
- R1 キャプチャ中のフック競合(通常ルートと奪い合い) → 対策: 切断点はroute_key/route_mouse冒頭の_capturing先行判定の単一箇所。キャプチャ中はroute_keyが全キーを消費(Escは取消・他は記録)し精密・マッピングに流さない
- R2 修飾キー単体押下の記録ブレ → 対策: 修飾単体はそのキー自体を記録、Escはキャプチャ取消に固定し記録不可。Escの割当はビルダー経由で可としUIに明示
- R3 Runキーとexeパス(開発時python実行と凍結exeの混同) → 対策: 凍結時のみ登録可、script実行時は無効表示。HKCUは管理者不要、失敗はUI表示、AV誤検知は配布手順に明記
- R4 反転の整合(一般タブで反転なし vs tilt反転既存) → 対策: tilt swap/invertはデバイス固有として割当タブ既存のまま。一般タブはカーソル/HID方向反転なし(SPIは方向を触らない事実)と明記
- R5 WinプリセットのMac流写し → 対策: 戻るAlt+Left・進むAlt+Right等Win既定に寄せる。Yuna仮説2の受入

招集判断の記録(Phase1):
- Hermes: 未招集。WH_KEYBOARD_LL/GetKeyState/winregは公開仕様でKaiが直接確認。呼ばなかった理由: 領域の事実確認が不要
- Gaia: 未招集。設計案分岐なし。呼ばなかった理由: 創発の種不足なし
- Artemis: 本Phase1計画で代替
- Daedalus: 招集。P1-1〜P1-5の実装を担当
- Metis: 実装後に招集。Hayatoゲート前に品質レビュー
- Athena: 未招集。統合はKai
- Yuna/Hayato: トライアングルと中間・最終ゲートで回す

## 自己検証計画（80%基準）

brief必須6件に対する検証:
- 必須1-2: 単体テストで各ButtonIDにKeyCombo保存とSendInput呼び出し分岐を確認
- 必須3-4: 精密トグル/ホールド状態遷移とスケール写像を単体テストで確認
- 必須5: JSON保存と再読込を単体テストで確認
- 必須6: Discoveryログ蓄積を単体テストで確認
- 6件中5件確認で83%でPASS。実機フックはWin環境での手動確認に委譲し明記する
