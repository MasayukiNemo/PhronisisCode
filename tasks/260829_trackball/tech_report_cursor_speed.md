# BSTBB700 精密カーソル速度調整 テクニカルレポート

## 1. 背景と要件

BSTBB700は高速慣性ホイール搭載のトラックボール。微細なポインタ操作のため、カーソル速度を一時的に落とす精密モードが必要だった。

要件:
- トグル（押すたびON/OFF）とホールド（押している間のみ）を択一で選択可能
- トリガーはキーボード未使用キー（F13等）またはマウス側（チルト左/中央/進む）から1つ
- スケールは10%〜100%をスライダーで可変、デフォルト25%
- 方向は物理と一致し、反転しないこと

## 2. 試行した方式と失敗の構造

### 2.1 CGEvent delta書き換え

```swift
// EventTapManager.swift:380-412 (precise path)
let origDx = event.getIntegerValueField(.mouseEventDeltaX)
var dxRaw = origDx
if hidInvertedX { dxRaw = -dxRaw }
let dx = cursorInverted ? -dxRaw : dxRaw
// ...
event.setIntegerValueField(.mouseEventDeltaX, value: adx)
event.location = nloc // cur - orig + adx
return Unmanaged.passUnretained(event)
```

- 期待: deltaを scale倍して返すことで減速
- 結果: TahoeのWindowServerは `kCGHIDEventTap` で `event.location` を正とし `delta` は付随情報として無視されると推定(Hermes検証)。`delta`だけ書き換えても移動量は変わらず、`location`を同時に書き換えても `headInsert` では反映されない。
- 副次障害: 低速域で `dx=1,2` を `scale 0.25` で `Int` に丸めると `0` が連続し、カーソルが微振動して macOSの「シェイクでカーソル拡大」を誤発火し、カーソルが異様に大きく見える。

### 2.2 CGWarpによる絶対位置打ち直し

```swift
let nloc = CGPoint(x: cur.x - CGFloat(origDx) + CGFloat(adx),
                   y: cur.y - CGFloat(origDy) + CGFloat(ady))
CGWarpMouseCursorPosition(nloc)
return nil // 元イベントを消費
```

- 期待: Warpは確実にカーソルを動かすため減速する
- 結果: 減速はするが上下左右が反転する。理由は Warpの跳躍ベクトルが `nloc - cur = adx - orig` になるため。`adx = orig * scale` で同符号かつ `|adx| < |orig|` のとき `adx - orig` は `orig` と逆符号になる。縮小時は必ず逆符号になるため、Warpは原理的に反転する。`scale<1` で遅くすればするほど逆符号は顕著になる。Hayatoの指摘通り「遅くする式で符号反転させてる矛盾」。
- さらに `CGWarp` と `CGEvent.location` は同じ global左上座標だが、`NSScreen.frame` で `screenH - y` と誤って反転させると上下が逆になる。`isWarping` ガードで次の物理イベント1点を潰すとカクつきも発生。Hermesが `screenH - y` は誤りと指摘し、Hayatoが BLOCK判定。

数値例:

```
orig = -14, adx = -4 (scale 0.285), cur = 668, nloc = 678
nloc - cur = 10 (右) だが origは左を示すはずで逆符号
display列 nloc_i - nloc_{i-1} = adx = -4 (左) だが、cur->nlocのjumpが逆に見えるためユーザは「反転」と知覚
```

### 2.3 システム設定 `com.apple.mouse.scaling` の一時変更

```bash
defaults write -g com.apple.mouse.scaling 0.5
killall cfprefsd
```

- 期待: システム設定を一時的に低値にすれば確実に遅くなる
- 結果: Tahoeでは `com.apple.mouse.scaling` が存在せず、存在しても `cfprefsd` 同期と WindowServer再読込に再ログインを要し、ホールドの100-500ms遅延に間に合わない。クラッシュ時に低速値が残留する永続リスクもある。Hayatoが「永続破損に近い」として WARN。

## 3. 採用した解決策: IOHIDServiceClient経由のシステム方式

LinearMouse/mouse-sensitivity と同方式。`IOHIDEventSystemClient` の private API `IOHIDServiceClientCopyProperty/SetProperty` で `HIDMouseAcceleration` を直接書き換える。`defaults` と異なり即時反映し、プロセスが保持する `IOHIDEventSystemClient` が生きている間だけ有効で、再起動で消えるため残留リスクが低い。

### 3.1 なぜこの方式である必要があるか

- `CGEventTap` の `delta/location` は Tahoeで無視されるか逆走すると推定されるため、EventTapレベルで減速を完結できないと判断
- `CGWarp` は縮小時は `nloc-cur=adx-orig` が逆符号になる数学的必然で逆走するため、減速と正方向を両立できない
- `defaults` は即時性と永続リスクでホールドに不適
- `IOHIDServiceClient` は WindowServerが参照する `HIDPointer` の加速テーブルを直接書き換えるため、確実に遅くなり方向も変わらない。LinearMouseが Tahoeでも `HIDMouseAcceleration` の writeは成功することを実証済み

### 3.2 実装

`SystemPointerSpeed.swift:1-151`（抜粋 8-35）

```swift
final class SystemPointerSpeed {
    static let shared = SystemPointerSpeed()
    private var savedAcceleration: Double?
    var isPreciseApplied = false // TODO: preciseInvertedと共にフォールバックWarp廃止時に削除

    func setPrecise(_ active: Bool, scale: Double = 0.25) {
        if active == isPreciseApplied { return }
        if active { applyPrecise(scale: scale) } else { restore() }
    }
    private func applyPrecise(scale: Double) {
        if savedAcceleration == nil { savedAcceleration = getAcceleration() }
        if let acc = savedAcceleration {
            let newAcc = max(0, acc * scale)
            setAcceleration(newAcc) // HIDMouseAcceleration = acc * scale
        } else {
            setAcceleration(0.2) // fallback
        }
        isPreciseApplied = true
    }
    private func restore() {
        if let acc = savedAcceleration { setAcceleration(acc) }
        isPreciseApplied = false
    }
}
```

`PreciseEngine.swift:8-13`

```swift
@Published var isActive: Bool = false {
    didSet {
        if oldValue != isActive {
            SystemPointerSpeed.shared.setPrecise(isActive, scale: scale)
        }
    }
}
var scale: Double { min(max(store.settings.preciseScale, 0.10), 1.0) }
```

`EventTapManager.swift:395-430`（フォールバック時のみWarp、通常はSystemPointerSpeedが有効なら素通し。UIのpreciseInvertedは除去したがコードはdeprecatedとして残留、TODOで削除予定）

```swift
if precise.isActive {
    if SystemPointerSpeed.shared.isPreciseApplied {
        return Unmanaged.passUnretained(event) // システム側で減速
    }
    // フォールバック: Warpで adx = dx*scale+rem を計算
    let sx = Double(dx) * scale + preciseRemainderX
    let outX0 = Int64(sx.rounded(.towardZero))
    preciseRemainderX = sx - Double(outX0)
    let adx = pInv ? -outX0 : outX0 // TODO: フォールバックWarp廃止時にpreciseInvertedごと削除
    let nloc = CGPoint(x: cur.x - CGFloat(origDx) + CGFloat(adx), ...)
    CGWarpMouseCursorPosition(nloc)
}
```

`AppDelegate.swift:33`

```swift
func applicationWillTerminate(_ notification: Notification) {
    SystemPointerSpeed.shared.setPrecise(false)
    eventTap.stop()
}
```

### 3.3 計算式の詳細（フォールバック時のみ）

フォールバックの Warp pathでは小数丸め誤差を `preciseRemainder` で補正する。正しいアキュムレータは以下。旧実装 `(dx+rem)*scale` は毎フレーム `rem*scale` で減衰し低速で永遠に0を出力するバグがあった。

```swift
// 正
let sx = Double(dx) * scale + preciseRemainderX
let outX0 = Int64(sx.rounded(.towardZero)) // 負数は towardZero で -2.5 -> -2
preciseRemainderX = sx - Double(outX0)
if abs(preciseRemainderX) > 2.0 { preciseRemainderX = 0 } // 発散ガード
```

`dx=2, scale=0.25` のとき `0.5+0.5+0.5+0.5=2` で4フレームで2px出力され、スタッタリングによるシェイク拡大を防ぐ。

### 3.4 IOHIDServiceClientの取得（private API）

```swift
let handle = dlopen("/System/Library/Frameworks/IOKit.framework/IOKit", RTLD_NOW)
let create = dlsym(handle, "IOHIDEventSystemClientCreate")
let client = create(kCFAllocatorDefault)
let services = IOHIDEventSystemClientCopyServices(client) // CFArray of IOHIDServiceClient
let key = IOHIDServiceClientCopyProperty(svc, kIOHIDPointerAccelerationTypeKey) as? String ?? "HIDMouseAcceleration"
IOHIDServiceClientSetProperty(svc, key, NSNumber(value: Int(newAcc*65536)))
```

Tahoeでは `kIOHIDPointerAccelerationTypeKey` の readが nullを返すことがあるが writeは成功する（LinearMouse #1052）。そのため fallbackで `HIDMouseAcceleration` に直接書き、read失敗時は `0.2` を仮置きする。

## 4. ハマりポイントと対策のまとめ

| ハマり | 原因 | 対策 | なぜその対策である必要があるか |
|---|---|---|---|
| delta書き換えで遅くならない | Tahoeで deltaが無視されると推定(Hermes検証) | IOHIDServiceClientで HIDMouseAcceleration を直接変更 | EventTapレベルではWindowServerがlocation駆動に変更したと推定されるため、推定が正しければ唯一確実に効くのがHID加速テーブル |
| Warpで逆走する | `adx-orig` が縮小時は逆符号になる数学的必然 | システム方式に一本化。フォールバック時のみ Warpを残すがコードは残留、UIのpInvは除去 | Warpは縮小時は原理的に逆走するため、減速と正方向を両立できない |
| Yだけ反転する | `screenH - y` で誤って反転 | Warpとevent.locationは同じglobal左上座標のため反転を削除 | Apple docで両者ともglobal左上と明記 |
| 低速でカーソルが大きくなる | `dx=1,2` が `Int` 丸めで `0` 連続し微振動してシェイク拡大を誤発火 | `preciseRemainder` で小数蓄積し `towardZero` で丸める | 微振動を無くさないとシェイク判定を回避できない |
| 進む/チルトのホールドが一瞬でOFF | キーボードエミュレーション(Ctrl+→)は autorepeat で keyDownが連続し、holdがトグルに見える | 進む/チルトはホールド不可としてトグルにフォールバック、中央のみホールド可 | 物理holdが取れないデバイス特性のため、仕様でトグルのみとするのが追従性が高い |
| チルトでトラックパッド二本指が誤爆 | scrollWheelの `isContinuous==1` がトラックパッド由来 | `scrollWheelEventIsContinuous` で除外 | チルトは離散的な `isContinuous==0` のみがトラックボール由来 |

## 5. 今後の拡張

- `filterByDevice` をONにしたとき、IOHIDの `VendorID/ProductID` と `CGEventTap` のタイムスタンプ相関（50ms窓）で BSTBB700由来のイベントだけを減速するデバイス限定化
- `HIDPointerResolution` による速度の線形調整（mouse-sensitivityの `--speed` 相当）
- `IOHIDEventSystemClient` を常駐させ再適用する daemon化（デバイス再接続時のリセット対策）

---
生成: 2026-08-31 / 対象: tasks/260829_trackball/BSTBB700Customizer/Sources/BSTBB700Customizer/{EventTapManager.swift:395-430/全体396-511, PreciseEngine.swift:8-17, SystemPointerSpeed.swift:1-151, MappingStore.swift:57-62} / UIのpreciseInvertedトグルとdebugLogは除去したがコードはフォールバック用にdeprecatedとして残留、TODOで削除予定
補足: 事実と推測の切り分けは Hermes検証に基づき「推定」と明記
