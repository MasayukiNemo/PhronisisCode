# BSTBB700 Customizer — BUFFALO BSTBB700 トラックボールカスタマイザー

macOS 13+ / Apple Silicon+Intel Universal / Bluetooth BSTBB700専用（DiscoveryログでVID/PID特定可能）
Swift 6.3 / AppKit+SwiftUI / CGEventTap主力 + IOHIDManager列挙補助 / CGEventPost / UserDefaults Codable / SMAppService

## 機能（brief.md 必須6件）

1. 5入力（戻る/進む/チルト左右/中央押し込み）それぞれに任意のキーコンボ（Cmd+C, Cmd+Shift+T, F13等）を割り当て可能
2. 修飾キー込み複数キー対応をCGEventPostでグローバルに発火
3. 精密モード: トグル or ホールド択一、トリガーは未使用キー(F13/F14/F15/CapsLock) or マウス(進む/チルト右)から1つ選択。排他制御で競合時は警告表示
4. 移動量スケール 10-100% スライダー、デフォルト30%、deltaを係数でスケール（加速カーブは触らない）
5. MenuBar常駐(NSStatusItem) + Settingsウィンドウ + HUD色変化(ON:緑/OFF:灰) + 再起動後もUserDefaults保持
6. BSTBB700 Bluetooth接続で動作確認用にDiscoveryログモード搭載（Button/Consumer/Keyboardどれで届くかを判別、VID/PID/transport表示、他マウス誤爆はフィルタOFFならグローバル、UIで「グローバル減速」明記）

## アーキテクチャ

```
[Bluetooth BSTBB700] -> macOS WindowServer -> CGEventTap(headInsert) -> Event Router -> MappingStore / PreciseEngine -> KeyEmitter(CGEventPost) -> UI(HUD/Settings)
                    \-> IOHIDManager (列挙のみ、Seizeしない) -> Discoveryログ
```

- IOHID Seizeは垂直ホイールまで奪うため不採用、相関窓50msで将来拡張余地のみ残す
- 精密モードはMVPではグローバル減速（UIで明記）、将来IOHID相関でデバイス限定に拡張可能

## 権限

- 入力監視(Input Monitoring) + アクセシビリティが必須。初回はPermissionViewでシステム設定へ誘導
- macOS 14+はCGPreflightPostEventAccessで事前チェック

## ビルド（Xcodeなし環境）

```bash
./build.sh              # swift build + .appバンドル生成 + ad-hoc署名
./build.sh --run        # ビルド後に起動
xattr -cr BSTBB700Customizer.app  # Gatekeeper回避（配布時）
```

Xcodeがある場合は `BSTBB700Customizer.xcodeproj` を開いてBuild（Sandbox OFF, LSUIElement=YES, ad-hoc署名）

### SwiftPMのみ

```bash
swift build
.build/debug/BSTBB700Customizer  # バイナリ直実行（Dockに出るがMenuBar常駐は同じ）
```

## 設定保存

- `UserDefaults`キー `bstbb700.settings.v1` にJSON Codableで保存
- `mappings: [ButtonID: KeyCombo]` / `preciseEnabled/Trigger/Mode/Scale` / `discoveryEnabled`

## 進む/戻るの扱い

- 未割り当て: `return event`で素通し（ブラウザのCmd+[ / Cmd+] を維持）
- 割り当てあり: `KeyEmitter.emit`後に`return nil`で横取り消費
- 失敗時は素通し維持にフォールバック（brief合意）

## 精密モード詳細

- トグル: トリガー押下でON/OFF反転、HUDで緑表示、MenuBarアイコンも緑に
- ホールド: 押している間のみ減速
- キーボードトリガは横取り消費（グローバルに漏らさない）
- マウストリガが進む/チルト右のときはキー割り当てと排他（Settingsで警告）

## 配布

- Sandbox OFF / Entitlementsなし / ad-hoc署名(`codesign -s -`)
- Gatekeeper回避: `xattr -cr` + 右クリック→開く。将来Developer ID取得時に公証に置換
- DMG/zip直配布 or Homebrew cask（任意）

## 既知の制約（MVP）

- 精密モードはグローバル減速（トラックパッド含む全ポインタが減速）。UIに明記済み
- VID/PIDフィルタはOFF。Discoveryで特定後に設定でONに拡張予定
- 水平チルトのみカスタム、垂直スクロールは常に素通し

## 開発メモ

- MenuBarExtraはXcode/SwiftUI 4.3前提のため、SwiftPM環境ではNSStatusItemで代替（機能同等）
- EventTapは`kCGHIDEventTap/headInsert/defaultTap`、無効化時は2秒ポーリングで再有効化
