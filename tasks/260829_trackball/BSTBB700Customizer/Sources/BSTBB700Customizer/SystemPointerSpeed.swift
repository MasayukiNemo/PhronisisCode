import Foundation
import IOKit
import IOKit.hidsystem
import CoreGraphics

/// SystemPointerSpeed — IOHIDServiceClient 経由でポインタ加速/解像度を一時変更する。
/// LinearMouse/mouse-sensitivity と同方式。MVPではグローバルに全デバイスへ適用し、OFFで復元する。
/// 参考: IOHIDServiceClientCopyProperty / IOHIDServiceClientSetProperty(kIOHIDPointerAccelerationTypeKey, HIDMouseAcceleration, HIDPointerResolution)
final class SystemPointerSpeed {
    static let shared = SystemPointerSpeed()
    private var savedAcceleration: Double?
    private var savedResolution: Double?
    var isPreciseApplied = false

    // IOHIDEventSystemClient (private) を使う。なければフォールバックで何もしない
    func setPrecise(_ active: Bool, scale: Double = 0.3) {
        if active == isPreciseApplied { return }
        if active {
            applyPrecise(scale: scale)
        } else {
            restore()
        }
    }

    private func applyPrecise(scale: Double) {
        // 既存値を保存
        if savedAcceleration == nil {
            savedAcceleration = getAcceleration()
        }
        if savedResolution == nil {
            savedResolution = getResolution()
        }
        // linear scalingで遅くする: accelerationをscale倍、resolutionも調整
        // mouse-sensitivity の --disable-acceleration 相当は acceleration -1 だが、ここでは通常加速を維持しつつ 0.25-1.0 にスケール
        // 簡易: HIDMouseAcceleration を scale倍にする
        if let acc = savedAcceleration {
            let newAcc = max(0.0, acc * scale)
            setAcceleration(newAcc)
            NSLog("[BSTBB700] SystemPointerSpeed apply precise scale=%.2f acc %.3f -> %.3f", scale, acc, newAcc)
        } else {
            // 読み取れない場合は直接 0.3 を試す
            setAcceleration(0.2)
            NSLog("[BSTBB700] SystemPointerSpeed apply precise fallback scale=%.2f", scale)
        }
        isPreciseApplied = true
    }

    private func restore() {
        guard isPreciseApplied else { return }
        if let acc = savedAcceleration {
            setAcceleration(acc)
            NSLog("[BSTBB700] SystemPointerSpeed restore acc=%.3f", acc)
        }
        if let res = savedResolution {
            setResolution(res)
        }
        // 保存は次回applyまで保持（再適用時に再取得しないためクリアしない）
        isPreciseApplied = false
    }

    // MARK: - IOHIDServiceClient helpers (private API via dlopen)

    private func getAcceleration() -> Double? {
        guard let services = copyServices() else { return nil }
        for svc in services {
            if let val = copyProperty(svc, key: kIOHIDPointerAccelerationTypeKey as String) as? String {
                // key自体が文字列値を持つ場合、実際のプロパティ名を取得
                if let num = copyProperty(svc, key: val) as? NSNumber {
                    return num.doubleValue / 65536.0
                }
            }
            if let num = copyProperty(svc, key: "HIDMouseAcceleration" as String) as? NSNumber {
                return num.doubleValue / 65536.0
            }
            if let num = copyProperty(svc, key: kIOHIDMouseAccelerationType as String) as? NSNumber {
                return num.doubleValue / 65536.0
            }
        }
        return nil
    }

    private func setAcceleration(_ v: Double) {
        let fixed = Int(v * 65536)
        guard let services = copyServices() else { return }
        for svc in services {
            // まず acceleration type を取得
            var key: String = "HIDMouseAcceleration"
            if let t = copyProperty(svc, key: kIOHIDPointerAccelerationTypeKey as String) as? String {
                key = t
            }
            setProperty(svc, key: key, value: NSNumber(value: fixed))
        }
    }

    private func getResolution() -> Double? {
        guard let services = copyServices() else { return nil }
        for svc in services {
            if let num = copyProperty(svc, key: "HIDPointerResolution" as String) as? NSNumber {
                return num.doubleValue
            }
        }
        return nil
    }

    private func setResolution(_ v: Double) {
        guard let services = copyServices() else { return }
        for svc in services {
            setProperty(svc, key: "HIDPointerResolution", value: NSNumber(value: v))
        }
    }

    // MARK: - Service enumeration via IOHIDEventSystemClient (private)

    private func copyServices() -> [AnyObject]? {
        // dlopenで private API を取得
        let handle = dlopen("/System/Library/Frameworks/IOKit.framework/IOKit", RTLD_NOW)
        guard handle != nil else { return nil }
        // IOHIDEventSystemClientCreate
        typealias CreateFunc = @convention(c) (CFAllocator?) -> UnsafeMutableRawPointer?
        guard let sym = dlsym(handle, "IOHIDEventSystemClientCreate") else { return nil }
        let create = unsafeBitCast(sym, to: CreateFunc.self)
        guard let client = create(kCFAllocatorDefault) else { return nil }
        // CopyServices
        typealias CopyFunc = @convention(c) (UnsafeMutableRawPointer?) -> CFArray?
        guard let sym2 = dlsym(handle, "IOHIDEventSystemClientCopyServices") else { return nil }
        let copy = unsafeBitCast(sym2, to: CopyFunc.self)
        guard let arr = copy(client) as? [AnyObject] else { return nil }
        // フィルタ: pointer acceleration を持つものだけ
        return arr.filter { svc in
            copyProperty(svc, key: "HIDMouseAcceleration") != nil || copyProperty(svc, key: kIOHIDPointerAccelerationTypeKey as String) != nil
        }
    }

    private func copyProperty(_ svc: AnyObject, key: String) -> AnyObject? {
        let handle = dlopen("/System/Library/Frameworks/IOKit.framework/IOKit", RTLD_NOW)
        guard handle != nil else { return nil }
        typealias CopyPropFunc = @convention(c) (AnyObject, CFString) -> AnyObject?
        guard let sym = dlsym(handle, "IOHIDServiceClientCopyProperty") else { return nil }
        let fn = unsafeBitCast(sym, to: CopyPropFunc.self)
        return fn(svc, key as CFString)
    }

    private func setProperty(_ svc: AnyObject, key: String, value: AnyObject) {
        let handle = dlopen("/System/Library/Frameworks/IOKit.framework/IOKit", RTLD_NOW)
        guard handle != nil else { return }
        typealias SetPropFunc = @convention(c) (AnyObject, CFString, AnyObject) -> Void
        guard let sym = dlsym(handle, "IOHIDServiceClientSetProperty") else { return }
        let fn = unsafeBitCast(sym, to: SetPropFunc.self)
        fn(svc, key as CFString, value)
    }
}
