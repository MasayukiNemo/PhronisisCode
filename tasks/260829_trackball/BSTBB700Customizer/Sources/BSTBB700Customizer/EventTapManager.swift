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
    private let selfPID = Int64(getpid())
    private let emitMagic: Int64 = 0xB700B700
    private var handlingDepth: Int32 = 0
    private var consecutiveTimeouts = 0
    private var lastEscapeTimes: [CFTimeInterval] = []
    private var lastLogTime: CFTimeInterval = 0

    // 相関窓: キーボード由来と区別するためのタイムスタンプ（将来拡張）
    private var lastIOHIDTimestamp: UInt64 = 0

    func setDiscovery(_ d: HIDDiscovery) { self.discovery = d }

    func start() {
        guard tap == nil else { return }
        guard canStartTap() else {
            NSLog("[BSTBB700] EventTap not started: Input Monitoring or Accessibility denied")
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

    /// 表示用: 3点すべてが揃っているか（AX + Listen + Post）
    func checkAccessibility() -> Bool {
        let trusted = AXIsProcessTrusted()
        let listenOK: Bool
        let postOK: Bool
        if #available(macOS 10.15, *) {
            listenOK = CGPreflightListenEventAccess()
            postOK = CGPreflightPostEventAccess()
        } else {
            listenOK = true
            postOK = true
        }
        return trusted && listenOK && postOK
    }

    /// 起動用: tap生成に必須なAX + Listenのみ（Postはemit時に必要だがtap生成は止めない）
    func canStartTap() -> Bool {
        let trusted = AXIsProcessTrusted()
        let listenOK: Bool
        if #available(macOS 10.15, *) {
            listenOK = CGPreflightListenEventAccess()
        } else {
            listenOK = true
        }
        return trusted && listenOK
    }

    func canEmit() -> Bool {
        if #available(macOS 10.15, *) {
            return CGPreflightPostEventAccess()
        }
        return AXIsProcessTrusted()
    }

    // MARK: - Core routing

    private func handle(proxy: CGEventTapProxy, type: CGEventType, event: CGEvent) -> Unmanaged<CGEvent>? {
        // 0. system disabledは即時復帰（5回連続ならフェイルセーフ停止）
        if type.rawValue == 0xFFFFFFFE || type.rawValue == 0xFFFFFFFD {
            consecutiveTimeouts += 1
            NSLog("[BSTBB700] tap disabled type=0x%X cnt=%d", type.rawValue, consecutiveTimeouts)
            if consecutiveTimeouts >= 5 {
                NSLog("[BSTBB700] 5 consecutive disables -> fail-safe stop")
                DispatchQueue.main.async { self.stop() }
                return Unmanaged.passUnretained(event)
            }
            if let t = tap { CGEvent.tapEnable(tap: t, enable: true) }
            return Unmanaged.passUnretained(event)
        }
        consecutiveTimeouts = 0

        // 1. kill-switch: /tmpファイルまたはEsc5連打で停止
        if FileManager.default.fileExists(atPath: "/tmp/disable-bstbb700") {
            return Unmanaged.passUnretained(event)
        }
        if type == .keyDown && event.getIntegerValueField(.keyboardEventKeycode) == 53 {
            let now = CFAbsoluteTimeGetCurrent()
            lastEscapeTimes.append(now)
            lastEscapeTimes = lastEscapeTimes.filter { now - $0 < 2.0 }
            if lastEscapeTimes.count >= 5 {
                NSLog("[BSTBB700] Esc x5 kill-switch -> stop tap")
                DispatchQueue.main.async { self.stop() }
                return Unmanaged.passUnretained(event)
            }
        }

        // 2. 自己生成イベントは素通し（PID + magic tagで再帰防止）
        if event.getIntegerValueField(.eventSourceUnixProcessID) == selfPID {
            return Unmanaged.passUnretained(event)
        }
        if event.getIntegerValueField(.eventSourceUserData) == emitMagic {
            return Unmanaged.passUnretained(event)
        }

        // 3. 再入ガード
        if handlingDepth != 0 {
            return Unmanaged.passUnretained(event)
        }
        handlingDepth += 1
        defer { handlingDepth -= 1 }

        // 4. watchdog: 20ms超過で警告
        let t0 = CFAbsoluteTimeGetCurrent()
        defer {
            let dt = CFAbsoluteTimeGetCurrent() - t0
            if dt > 0.02 { NSLog("[BSTBB700] slow handle %.4f type=%d", dt, type.rawValue) }
        }

        let store = MappingStore.shared
        let precise = PreciseEngine.shared

        // Discoveryログ（20Hz throttle）
        if store.settings.discoveryEnabled {
            let now = CFAbsoluteTimeGetCurrent()
            if now - lastLogTime > 0.05 {
                lastLogTime = now
                logEvent(type: type, event: event)
            }
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
                let inverted = MappingStore.shared.settings.tiltInverted
                let rawRight = h > 0
                let isRight = inverted ? !rawRight : rawRight
                let tiltButton: ButtonID = isRight ? .tiltRight : .tiltLeft
                // 精密トリガー消費（左右どちらも対応、Eitherなら両方）
                if precise.handleMouseTrigger(button: tiltButton, isDown: true) {
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
            if precise.isActive {
                let s = min(max(MappingStore.shared.settings.preciseScale, 0.25), 1.0)
                if s < 0.99 {
                    let dx = event.getDoubleValueField(.mouseEventDeltaX) * s
                    let dy = event.getDoubleValueField(.mouseEventDeltaY) * s
                    event.setDoubleValueField(.mouseEventDeltaX, value: dx)
                    event.setDoubleValueField(.mouseEventDeltaY, value: dy)
                }
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
        lastEventDescription = msg
    }
}
