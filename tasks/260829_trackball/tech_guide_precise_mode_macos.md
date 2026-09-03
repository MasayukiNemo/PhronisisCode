# macOSでカーソルを一時的に遅くする精密モード実装ガイド

## 1. 要件

- カーソル速度を一時的に落とす精密モードを提供する
- トグル（押すたびON/OFF）とホールド（押している間のみ）を選択可能にする
- スケールは10%〜100%で可変にする

## 2. 試行した方式と結果

### 2.1 CGEventのdelta書き換え

`CGEventTap` で `kCGHIDEventTap` を `headInsert` で取得し、`mouseMoved` の `deltaX/Y` を係数で縮小して返す方式。

```swift
let dx = event.getIntegerValueField(.mouseEventDeltaX)
let adx = Int64(Double(dx) * scale)
event.setIntegerValueField(.mouseEventDeltaX, value: adx)
return Unmanaged.passUnretained(event)
```

結果: macOS Tahoeでは `delta` の書き換えが移動量に反映されない。`location` を同時に書き換えても `headInsert` では反映されないことがある。低速域で `dx=1` を `scale 0.25` で丸めると `0` が連続し、カーソルが微振動して「シェイクでカーソルを拡大」機能を誤発火する。

### 2.2 CGWarpによる絶対位置の打ち直し

```swift
let nloc = CGPoint(x: cur.x - origDx + adx, y: cur.y - origDy + ady)
CGWarpMouseCursorPosition(nloc)
return nil
```

結果: 減速はするが、縮小時は `nloc - cur = adx - orig` が `orig` と逆符号になるため反転して見える。`adx = orig * scale` で同符号かつ `|adx| < |orig|` のとき、Warpの跳躍は必ず逆符号になる。原理的に減速と正方向を両立できない。

### 2.3 システム設定 `com.apple.mouse.scaling` の一時変更

```bash
defaults write -g com.apple.mouse.scaling 0.5
killall cfprefsd
```

結果: 再ログインを要し、ホールドの数百msに間に合わない。クラッシュ時に低速値が残留するリスクがある。

## 3. 採用する方式: IOHIDServiceClient経由

`IOHIDEventSystemClient` の `IOHIDServiceClientCopyProperty` / `IOHIDServiceClientSetProperty` で `HIDMouseAcceleration` を直接変更する。`defaults` と異なり即時反映し、プロセスが保持するクライアントが生きている間だけ有効。

### 3.1 実装例（要点のみ、エラーハンドリングは省略）

```swift
import IOKit
import CoreGraphics

// IOKit private APIは dlopen/dlsym で取得するか、IOKit.framework のヘッダを直接importする
// 下記は LinearMouse/mouse-sensitivity と同等の擬似コード。実際は CFArray の取得と型キャストが必要

func setPrecise(active: Bool, scale: Double, saved: inout [String: Double]) {
    guard let client = IOHIDEventSystemClientCreate(kCFAllocatorDefault, nil) else { return }
    // clientは精密モード中は保持し、再適用や復元に使う。使い捨てにすると値がすぐ戻る
    guard let services = IOHIDEventSystemClientCopyServices(client) as? [AnyObject] else { return }
    for svc in services {
        // デバイスが加速タイプを公開しているか確認。Tahoeでは readが nullでも writeは成功する
        let typeKey = kIOHIDPointerAccelerationTypeKey as String
        let propKey = (IOHIDServiceClientCopyProperty(svc as! IOHIDServiceClientRef, typeKey as CFString) as? String) ?? "HIDMouseAcceleration"
        if active {
            if saved[propKey] == nil, let cur = IOHIDServiceClientCopyProperty(svc as! IOHIDServiceClientRef, propKey as CFString) as? NSNumber {
                saved[propKey] = cur.doubleValue / 65536.0 // IOFixed 16.16
            }
            let base = saved[propKey] ?? 0.3
            let fixed = Int((base * scale) * 65536) // scale 0.25なら 25%に
            IOHIDServiceClientSetProperty(svc as! IOHIDServiceClientRef, propKey as CFString, NSNumber(value: fixed) as CFNumber)
        } else if let base = saved[propKey] {
            let fixed = Int(base * 65536)
            IOHIDServiceClientSetProperty(svc as! IOHIDServiceClientRef, propKey as CFString, NSNumber(value: fixed) as CFNumber)
        }
    }
    // 注意: IOHIDServiceClientによる変更は永続化される。applicationWillTerminateだけでなく
    // signal(SIGTERM/SIGINT)や異常終了でも復元しないと低速が残留する。atexit/signalハンドラと UserDefaultsへの保存で二重に復元する
}
```

取得は `dlopen("/System/Library/Frameworks/IOKit.framework/IOKit")` と `dlsym` で private APIを取得する。Tahoeでは `kIOHIDPointerAccelerationTypeKey` の readが nullを返すことがあるが writeは成功するため、`HIDMouseAcceleration` にフォールバックし、read失敗時は `0.2` を仮置きする。

`scale` は `HIDMouseAcceleration` の値を `scale` 倍する。`0.25` なら `acc * 0.25` で 25%の速度になる。`HIDPointerResolution` を併用すれば線形な速度調整も可能。

### 3.2 小数丸めの補正（フォールバックでWarpを使う場合のみ）

Warpをフォールバックとして残す場合、低速域の `0` 連続を防ぐため小数余りを蓄積する。

```swift
let sx = Double(dx) * scale + remainderX
let out = Int64(sx.rounded(.towardZero))
remainderX = sx - Double(out)
if abs(remainderX) > 2.0 { remainderX = 0 }
```

`dx=2, scale=0.25` のとき `0.5+0.5+0.5+0.5=2` で4フレームで2px出力される。

## 4. 注意点

- ホールドはキーボードエミュレーション（例: `Ctrl+→`）では `autorepeat` で押しっぱなしが取れない。中央ボタンのような `otherMouseDown` で `down/up` が正しく取れる入力のみホールドに適する。チルトは `scrollWheel` で `up` がないためトグルのみにする。
- チルトでトラックパッドの二本指スワイプが誤爆する場合は `scrollWheelEventIsContinuous == 1` を除外する。
- アプリ終了時に必ず元の加速値を復元する。`applicationWillTerminate` で `setPrecise(false)` を呼ぶ。

## 5. 今後の拡張

- `VendorID/ProductID` とタイムスタンプ相関で特定デバイスのみを減速する
- `HIDPointerResolution` による線形速度調整
- `IOHIDEventSystemClient` を常駐させ再適用する

