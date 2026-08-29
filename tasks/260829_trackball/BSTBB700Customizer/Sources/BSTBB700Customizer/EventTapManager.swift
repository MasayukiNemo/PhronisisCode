import Foundation
import CoreGraphics
import AppKit
import Combine

/// CGEventTap主力エンジン。IOHID列挙は補助。mask: otherMouseDown/Up, scrollWheel, mouseMoved/dragged, keyDown/Up(精密トリガー判定用)
final class EventTapManager: ObservableObject {
    static let shared = EventTapManager()

    @Published var isRunning: Bool = false
    @Published var lastEventDescription: String = ""

    private var tap: CFMachPort?
    private var runLoopSource: CFRunLoopSource?
    private var discovery: HIDDiscovery?
    private var reenableTimer: Timer?

    // 相関窓: キーボード由来と区別するためのタイムスタンプ（将来拡張）
    private var lastIOHIDTimestamp: UInt64 = 0

    func setDiscovery(_ d: HIDDiscovery) { self.discovery = d }

    func start() {
        guard tap == nil else { return }
        guard checkAccessibility() else {
            NSLog("[BSTBB700] EventTap not started: accessibility denied")
            return
        }

        let mask: CGEventMask =
            (1 << CGEventType.otherMouseDown.rawValue) |
            (1 << CGEventType.otherMouseUp.rawValue) |
            (1 << CGEventType.scrollWheel.rawValue) |
            (1 << CGEventType.mouseMoved.rawValue) |
            (1 << CGEventType.leftMouseDragged.rawValue) |
            (1 << CGEventType.rightMouseDragged.rawValue) |
            (1 << CGEventType.otherMouseDragged.rawValue) |
            (1 << CGEventType.keyDown.rawValue) |
            (1 << CGEventType.keyUp.rawValue) |
            (1 << CGEventType.flagsChanged.rawValue)

        let callback: CGEventTapCallBack = { proxy, type, event, refcon in
            guard let refcon else { return Unmanaged.passUnretained(event) }
            let me = Unmanaged<EventTapManager>.fromOpaque(refcon).takeUnretainedValue()
            return me.handle(proxy: proxy, type: type, event: event)
        }

        let ref = Unmanaged.passUnretained(self).toOpaque()
        guard let t = CGEvent.tapCreate(tap: .cghidEventTap,
                                        place: .headInsertEventTap,
                                        options: .defaultTap,
                                        eventsOfInterest: mask,
                                        callback: callback,
                                        userInfo: ref) else {
            NSLog("[BSTBB700] CGEvent.tapCreate failed — check Input Monitoring permission")
            return
        }
        self.tap = t
        self.runLoopSource = CFMachPortCreateRunLoopSource(kCFAllocatorDefault, t, 0)
        CFRunLoopAddSource(CFRunLoopGetMain(), runLoopSource, .commonModes)
        CGEvent.tapEnable(tap: t, enable: true)
        isRunning = true
        NSLog("[BSTBB700] EventTap started")

        reenableTimer?.invalidate()
        reenableTimer = Timer.scheduledTimer(withTimeInterval: 2.0, repeats: true) { [weak self] _ in
            self?.reenableIfNeeded()
        }
    }

    func stop() {
        reenableTimer?.invalidate()
        reenableTimer = nil
        if let s = runLoopSource {
            CFRunLoopRemoveSource(CFRunLoopGetMain(), s, .commonModes)
        }
        if let t = tap {
            CGEvent.tapEnable(tap: t, enable: false)
            CFMachPortInvalidate(t)
        }
        tap = nil
        runLoopSource = nil
        isRunning = false
        NSLog("[BSTBB700] EventTap stopped")
    }

    private func reenableIfNeeded() {
        guard let t = tap else { return }
        if !CGEvent.tapIsEnabled(tap: t) {
            NSLog("[BSTBB700] tap disabled, re-enabling")
            CGEvent.tapEnable(tap: t, enable: true)
        }
    }

    func checkAccessibility() -> Bool {
        // AXIsProcessTrusted + CGPreflight
        let trusted = AXIsProcessTrusted()
        if #available(macOS 14.0, *) {
            let postOK = CGPreflightPostEventAccess()
            return trusted && postOK
        }
        return trusted
    }

    // MARK: - Core routing

    private func handle(proxy: CGEventTapProxy, type: CGEventType, event: CGEvent) -> Unmanaged<CGEvent>? {
        let store = MappingStore.shared
        let precise = PreciseEngine.shared

        // Discoveryログ
        if store.settings.discoveryEnabled {
            logEvent(type: type, event: event)
        }

        switch type {
        case .keyDown:
            let kc = UInt16(event.getIntegerValueField(.keyboardEventKeycode))
            // 精密トリガーがキーボードなら消費
            if precise.handleKeyboardTrigger(keyCode: kc, isDown: true) {
                return nil
            }
            return Unmanaged.passUnretained(event)

        case .keyUp:
            let kc = UInt16(event.getIntegerValueField(.keyboardEventKeycode))
            if precise.handleKeyboardTrigger(keyCode: kc, isDown: false) {
                return nil
            }
            return Unmanaged.passUnretained(event)

        case .flagsChanged:
            // CapsLockはflagsChangedで届く。alphaShiftフラグ変化でトグル
            let kc = UInt16(event.getIntegerValueField(.keyboardEventKeycode))
            if kc == 57 {
                // CapsLockは押下でflagsChangedが来る。downとして扱う
                if precise.handleCapsLockFlagsChanged(event: event) {
                    return nil
                }
            }
            return Unmanaged.passUnretained(event)

        case .otherMouseDown:
            let btn = Int64(event.getIntegerValueField(.mouseEventButtonNumber))
            let buttonID = buttonIDForCGButton(btn)
            if let bid = buttonID {
                // 精密トリガー消費チェック（マウス）
                if precise.handleMouseTrigger(button: bid, isDown: true) {
                    return nil
                }
                // 排他: 精密トリガーに使われているならMapping無視
                if store.isPreciseTriggerConsuming(button: bid) {
                    return nil
                }
                if let combo = store.mapping(for: bid) {
                    KeyEmitter.emit(combo: combo)
                    return nil // 横取り消費
                }
            }
            return Unmanaged.passUnretained(event)

        case .otherMouseUp:
            let btn = Int64(event.getIntegerValueField(.mouseEventButtonNumber))
            if let bid = buttonIDForCGButton(btn) {
                if precise.handleMouseTrigger(button: bid, isDown: false) {
                    return nil
                }
                if store.mapping(for: bid) != nil || store.isPreciseTriggerConsuming(button: bid) {
                    return nil
                }
            }
            return Unmanaged.passUnretained(event)

        case .scrollWheel:
            // チルト判定: horizontal deltaがあればチルト
            let h = event.getDoubleValueField(.scrollWheelEventPointDeltaAxis2)
            let v = event.getDoubleValueField(.scrollWheelEventPointDeltaAxis1)
            let isHorizontalTilt = abs(h) > 0.05 && abs(v) < 0.1
            let isVertical = abs(v) >= 0.05

            if isHorizontalTilt {
                let tiltButton: ButtonID = h > 0 ? .tiltRight : .tiltLeft
                // 精密トリガーがチルト右なら消費
                if tiltButton == .tiltRight, precise.handleMouseTrigger(button: tiltButton, isDown: true) {
                    // tiltは押下離上が分かれないため、toggleなら一発、holdなら押下扱い
                    // holdのリリースは次イベントで? 簡易: tiltはtoggleのみ推奨
                    return nil
                }
                if store.isPreciseTriggerConsuming(button: tiltButton) {
                    return nil
                }
                if let combo = store.mapping(for: tiltButton) {
                    KeyEmitter.emit(combo: combo)
                    return nil
                }
                // 未割り当ては素通ししない? 要件: チルトはHのみカスタム、V素通し。水平未割り当ては素通ししない方が安全だが、ブラウザ水平スクロールを殺さないため素通し。
                // ここでは未割り当ては素通し
                return Unmanaged.passUnretained(event)
            }
            if isVertical {
                // 垂直は常に素通し（将来オプションで抑止可能）
                return Unmanaged.passUnretained(event)
            }
            return Unmanaged.passUnretained(event)

        case .mouseMoved, .leftMouseDragged, .rightMouseDragged, .otherMouseDragged:
            // 精密モード中はdeltaを同期的に1回だけスケール。Taskは使わない（Use-after-return回避）
            if precise.isActive {
                let s = min(max(MappingStore.shared.settings.preciseScale, 0.1), 1.0)
                let dx = event.getDoubleValueField(.mouseEventDeltaX) * s
                let dy = event.getDoubleValueField(.mouseEventDeltaY) * s
                event.setDoubleValueField(.mouseEventDeltaX, value: dx)
                event.setDoubleValueField(.mouseEventDeltaY, value: dy)
            }
            return Unmanaged.passUnretained(event)

        default:
            return Unmanaged.passUnretained(event)
        }
    }

    private func buttonIDForCGButton(_ n: Int64) -> ButtonID? {
        switch n {
        case 2: return .center
        case 3: return .back
        case 4: return .forward
        default: return nil
        }
    }

    private func logEvent(type: CGEventType, event: CGEvent) {
        let btn = event.getIntegerValueField(.mouseEventButtonNumber)
        let kc = event.getIntegerValueField(.keyboardEventKeycode)
        let h = event.getDoubleValueField(.scrollWheelEventPointDeltaAxis2)
        let v = event.getDoubleValueField(.scrollWheelEventPointDeltaAxis1)
        let flags = event.flags.rawValue
        let msg = "type=\(type.rawValue) btn=\(btn) key=\(kc) h=\(String(format: "%.2f", h)) v=\(String(format: "%.2f", v)) flags=\(flags)"
        discovery?.append(msg)
        DispatchQueue.main.async { [weak self] in self?.lastEventDescription = msg }
    }
}
