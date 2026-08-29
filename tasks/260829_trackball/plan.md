# plan.md — 実装計画

## アーキテクチャ

```
[Bluetooth BSTBB700] --HID--> [macOS WindowServer] --CGEvent--> [TrackballCustomizer.app]
                                                                |
                                     +--------------------------+--------------------------+
                                     |                          |                          |
                              [HID Discovery]            [CGEventTap Engine]        [Permission Guide]
                              IOHIDManager列挙           kCGHIDEventTap              InputMonitoring
                              VID/PID/Transport          headInsert                  PostEvent/AX
                              UsagePage/Usageログ        mask: otherMouse/scroll    TCCチェック+設定誘導
                                                         /mouseMoved
                                     |                          |
                                     +------------+-------------+
                                                  |
                                          [Event Router]
                                          - ButtonID(2..5) -> Mapping
                                          - Tilt H/V判別 (axis2/axis1)
                                          - Discovery相関(50ms窓)でキーボード誤爆除外
                                          - 精密トリガー判定(トグル/ホールド択一)
                                                  |
                                   +--------------+--------------+
                                   |                             |
                            [Mapping Store]               [Precise Engine]
                            UserDefaults+JSON            deltaX/Y * scale(0.1-1.0)
                            button->KeyCombo             CGEvent delta書き換え
                            tilt->KeyCombo               トグル状態/ホールド状態管理
                            trigger/mode/scale           HUD連動
                                   |                             |
                                   +--------------+--------------+
                                                  |
                                          [Key Emitter]
                                          CGEventCreateKeyboardEvent
                                          flags+keyCode -> CGEventPost
                                                  |
                                          [UI Layer]
                                          MenuBarExtra(window) + SettingsView + HUD overlay
                                          + SMAppService LoginItem + UserDefaults永続化
```

技術選定:
- 言語: Swift 5.10+ / SwiftUI + AppKit (MenuBarExtraはSwiftUI, CGEventTapはAppKit/CFRunLoop)
- 取得: CGEventTap主力 (kCGHIDEventTap, headInsert, defaultTap) + IOHIDManagerは列挙/Discoveryのみ。Seizeしない
- 送信: CGEventCreateKeyboardEvent + CGEventPost(.cghidEventTap)、14+ではCGPreflightPostEventAccessで権限確認
- 保存: ObservableObject + UserDefaults(JSON Codable)。キーコンボは flags(UInt64)+keyCode(UInt16)でCodable
- 常駐: MenuBarExtra(.window) + LSUIElement=YES、AppDelegateでCFMachPortRunLoopSource登録、tap無効化時の再有効化ループ
- 署名: ad-hoc (codesign -s -)、Sandbox OFF、Entitlementsなし。配布はzip/DMG + `xattr -cr` + 右クリック開くでGatekeeper回避。将来的にDeveloper IDに置換

トレードオフ:
- IOHID Seizeで完全分離できるが垂直ホイールまで奪うため捨て、相関窓で妥協
- 精密モードは公開APIでは全デバイス減速になるが、MVPでは仕様としてUIに明記し、将来IOHID相関でデバイス限定に拡張可能にしておく
- トグル/ホールド同時はUX複雑化のため択一。トリガー排他チェックで進む/チルト右が精密トリガー時はキー割り当てと競合エラー表示

## タスク分解

1. [ ] T1 プロジェクト雛形: Xcodeプロジェクト生成 (BundleID: com.buffalo.bstbb700.customizer)、SwiftUI App + MenuBarExtra + LSUIElement、Sandbox OFF、ad-hoc署名確認、UserDefaultsストア雛形
2. [ ] T2 Discoveryログモード: IOHIDManager列挙 + CGEventTapログView (ButtonID, scrollWheel axis, keyDown keyCode/flags, timestamp) をUIに表示し、BSTBB700のVID/PIDと进む戻るのUsagePage/Usageを特定可能に
3. [ ] T3 CGEventTapエンジン: CFMachPortCreate + RunLoopSource + mask(otherMouseDown/Up, scrollWheel, mouseMoved/dragged) + tap無効化再有効化 + TCCチェック
4. [ ] T4 マッピング永続化: KeyCombo(Codable) + MappingStore(ボタン5種+チルト2方向) + トリガー/モード/scale保存 + 競合排他バリデーション
5. [ ] T5 キーエミッタ: CGEventCreateKeyboardEventで修飾+キー送信、フラグ/キーコード変換、PostEvent権限チェック、無音失敗ログ
6. [ ] T6 イベントルータ: ButtonID->KeyCombo、チルトH判定( |h|>0.1 && |v|<0.1 )でキー送信 or 素通し、未割り当てはreturn event(素通し)、割り当て時はreturn nil(消費)。精密トリガー判定とEvent Router統合
7. [ ] T7 精密エンジン: mouseMoved/draggedのdelta書き換え(scale 0.1-1.0)、トグル状態管理、ホールドはトリガーkeyDown/upでON/OFF、HUD連動、UIスライダー、グローバル減速の注意書き
8. [ ] T8 UI: MenuBarExtra Popover(HUD色変化+精密トグル表示) + SettingsWindow(5ボタン+チルト左右のKeyComboキャプチャUI + 精密モードセクション + スライダー + Discoveryログタブ)
9. [ ] T9 権限ガイド + 自動起動: TCCチェック画面 (InputMonitoring/PostEvent未許可時に設定リンク)、SMAppService loginItemトグル、初回起動ガイド、無効化通知バナー
10. [ ] T10 検証: 実機BSTBB700での手動検証 (5ボタン各割り当て、チルト、精密トグル/ホールド、スケール変更、素通し確認、再起動保持)、`scripts/code_health_check.py --no-color` 通過

## 依存関係

```
T1 -> T2 -> T3 -> T4 -> T5 -> T6 -> T7 -> T8 -> T9 -> T10
          T2 -+-> T6 (Discovery結果でルータ分岐を決定)
               T4 -> T6, T7, T8
               T3 -> T6, T7
```

MVPクリティカルパス: T1-T3-T4-T6-T7-T8 で最小動作。T2は実機特定のため必須、T5はT6から呼出し、T9はT10前に必須

## リスク

- R1 進む戻るがKeyboard 0x07エミュレーションでCGEventでは区別不能 → 対策: T2 DiscoveryでUsage特定、T6でIOHID相関50ms窓で軽減。ダメなら素通し維持をデフォルトにフォールバック (briefで合意済み)
- R2 精密モードがトラックパッドまで減速 → 対策: UIに明記、将来デバイス限定トグルでIOHID相関拡張。MVPでは仕様として受容
- R3 TCC未許可でCGEventTapCreateがNULL → 対策: T3で早期検出しT9ガイドで設定誘導、再起動不要のTahoe動作を確認
- R4 署名なしでGatekeeper BLOCK → 対策: ad-hoc署名 + 配布READMEに `xattr -cr` と右クリック開く手順を明記、将来Developer ID取得で置換
- R5 tapがkCGEventTapDisabledByTimeoutで無効化 → 対策: 通知監視でCGEventTapEnable再有効化ループ、RunLoop commonModes登録
- R6 トリガー排他(進む/チルト右を精密兼用) → 対策: T4でバリデーション、競合時にSettingsで警告表示

## 招集判断の記録

- Hermes: 招集済み。CGEventTap/IOHID/権限/Sandboxの技術検証を完了しplanに反映
- Gaia: 未招集。設計案分岐がなくHermes結果でアーキが一意に決まったため。呼ばなかった理由: トレードオフが少なく創発の種不足なし
- Artemis: 本planで代替。3ファイル以上の変更は確実だが仕様確定前は計画のみでDaedalusに委任
- Daedalus: 次フェーズで招集。T1-T10の実装を担当
- Metis: 次フェーズで招集。実装後の品質レビューでHayatoゲート前に指摘
- Athena: 未招集。統合はKaiが担う。2神以上並列出力の統合が必要になったら招集
- Yuna/Hayato: トライアングルで回し済み。Hayato中間軽量チェックを次に実施

## 自己検証計画（80%基準）

brief必須6件に対する検証:
- 必須1-2: 実機で各ボタン/チルトにCmd+C等の割り当てが効くことを手動確認 + ログでsendイベント確認
- 必須3-4: 精密トグルとホールドの切替、スライダー10/30/100%で移動量変化を手動確認
- 必須5: 設定変更→再起動後もUserDefaults保持を確認
- 必須6: BSTBB700接続時のみ動作、DiscoveryログでVID/PID確認、グローバル減速の明記をUIで確認
- 6件中5件確認で83%でPASS
