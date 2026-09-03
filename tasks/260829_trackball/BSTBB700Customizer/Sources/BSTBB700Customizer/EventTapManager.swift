import Foundation
import CoreGraphics
import AppKit
import Combine

/// CGEventTap主力エンジン。IOHID列挙は補助。mask: otherMouseDown/Up, scrollWheel, mouseMoved/dragged, keyDown/Up(精密トリガー判定用)
final class EventTapManager: ObservableObject {
    static let shared = EventTapManager()

    @Published var isRunning: Bool = false
    @Published var lastEventDescription: String = ""
    @Published var lastMouseDelta: (dx: Int64, dy: Int64, scaledDx: Int64, scaledDy: Int64, isPrecise: Bool) = (0,0,0,0,false)

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
    private var lastTiltTime: CFTimeInterval = 0
    private var lastDeltaTime: CFTimeInterval = 0
    private var debugLogEnabled = false
    var isDebugLogEnabled: Bool { debugLogEnabled }
    private var debugLogFile: FileHandle?
    private var preciseRemainderX: Double = 0
    private var preciseRemainderY: Double = 0
    private var warpRemainderX: Double { get { preciseRemainderX } set { preciseRemainderX = newValue } }
    private var warpRemainderY: Double { get { preciseRemainderY } set { preciseRemainderY = newValue } }
    private var isWarping = false

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
        // Warp直後の0.25s抑制を無効化
        if let src = CGEventSource(stateID: .hidSystemState) {
            src.localEventsSuppressionInterval = 0.0
        }
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

    func setDebugLogEnabled(_ enabled: Bool) {
        debugLogEnabled = enabled
        if enabled {
            let path = "/tmp/bstbb700_debug.log"
            FileManager.default.createFile(atPath: path, contents: nil)
            // forWritingAtPath is deprecated and can return nil on APFS; use URL-based API
            if let fh = FileHandle(forWritingAtPath: path) {
                debugLogFile = fh
            } else {
                do {
                    let url = URL(fileURLWithPath: path)
                    debugLogFile = try FileHandle(forWritingTo: url)
                    try debugLogFile?.truncate(atOffset: 0)
                } catch {
                    NSLog("[BSTBB700] debug log open failed: \(error)")
                    debugLogFile = nil
                }
            }
            NSLog("[BSTBB700] debug log enabled at \(path) fh=\(debugLogFile != nil ? "ok" : "nil")")
        } else {
            try? debugLogFile?.close()
            debugLogFile = nil
            NSLog("[BSTBB700] debug log disabled")
        }
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
            let flags = event.flags
            let isRepeat = event.getIntegerValueField(.keyboardEventAutorepeat) != 0
            // BSTBB700特殊仕様: 進む/戻るが Ctrl+→/Ctrl+← として送られる。キーボードのShift付き等は誤爆しないよう厳密にCtrlのみを判定
            let isCtrlOnly = flags.contains(.maskControl) && !flags.contains(.maskShift) && !flags.contains(.maskCommand) && !flags.contains(.maskAlternate)
            if isCtrlOnly && kc == 124 {
                if isRepeat { return nil }
                if precise.handleMouseTrigger(button: .forward, isDown: true) { return nil }
                if store.isPreciseTriggerConsuming(button: .forward) { return nil }
                if let combo = store.mapping(for: .forward) {
                    KeyEmitter.emit(combo: combo)
                    return nil
                }
            }
            if isCtrlOnly && kc == 123 {
                // Ctrl+← = 戻る
                if precise.handleMouseTrigger(button: .back, isDown: true) { return nil }
                if store.isPreciseTriggerConsuming(button: .back) { return nil }
                if let combo = store.mapping(for: .back) {
                    KeyEmitter.emit(combo: combo)
                    return nil
                }
            }
            // 旧仕様の⌘]/⌘[もフォールバックで対応
            if store.settings.preciseTrigger == .mouseForward, flags.contains(.maskCommand), kc == 30 {
                if precise.handleMouseTrigger(button: .forward, isDown: true) { return nil }
            }
            if precise.handleKeyboardTrigger(keyCode: kc, isDown: true) {
                return nil
            }
            return Unmanaged.passUnretained(event)

        case .keyUp:
            let kc = UInt16(event.getIntegerValueField(.keyboardEventKeycode))
            let flagsUp = event.flags
            let isCtrlOnlyUp = flagsUp.contains(.maskControl) && !flagsUp.contains(.maskShift) && !flagsUp.contains(.maskCommand) && !flagsUp.contains(.maskAlternate)
            if isCtrlOnlyUp && kc == 124 {
                if precise.handleMouseTrigger(button: .forward, isDown: false) { return nil }
                if store.mapping(for: .forward) != nil || store.isPreciseTriggerConsuming(button: .forward) { return nil }
            }
            if isCtrlOnlyUp && kc == 123 {
                if precise.handleMouseTrigger(button: .back, isDown: false) { return nil }
                if store.mapping(for: .back) != nil || store.isPreciseTriggerConsuming(button: .back) { return nil }
            }
            if store.settings.preciseTrigger == .mouseForward, flagsUp.contains(.maskCommand), kc == 30 {
                if precise.handleMouseTrigger(button: .forward, isDown: false) { return nil }
            }
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
            // トラックパッドの二本指スワイプは isContinuous=1 で区別しチルト誤爆を防ぐ
            let isContinuous = event.getIntegerValueField(.scrollWheelEventIsContinuous) != 0
            if isContinuous {
                return Unmanaged.passUnretained(event)
            }
            let h = event.getDoubleValueField(.scrollWheelEventPointDeltaAxis2)
            let v = event.getDoubleValueField(.scrollWheelEventPointDeltaAxis1)
            let isHorizontalTilt = abs(h) > 0.05 && abs(v) < 0.1
            let isVertical = abs(v) >= 0.05

            if isHorizontalTilt {
                let now = CFAbsoluteTimeGetCurrent()
                // 0.3秒デバウンスで連射防止（Spaces設定OFFでも誤爆を抑える）
                if now - lastTiltTime < 0.3 {
                    return Unmanaged.passUnretained(event)
                }
                lastTiltTime = now
                let inverted = MappingStore.shared.settings.tiltInverted
                let rawRight = h > 0
                let isRight = inverted ? !rawRight : rawRight
                let tiltButton: ButtonID = isRight ? .tiltRight : .tiltLeft
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
            let origDx = event.getIntegerValueField(.mouseEventDeltaX)
            let origDy = event.getIntegerValueField(.mouseEventDeltaY)
            var dxRaw = origDx
            var dyRaw = origDy
            if MappingStore.shared.settings.hidInvertedX { dxRaw = -dxRaw }
            if MappingStore.shared.settings.hidInvertedY { dyRaw = -dyRaw }
            let s = MappingStore.shared.settings
            let invX = s.cursorInverted || s.cursorInvertedX
            let invY = s.cursorInverted || s.cursorInvertedY
            let dx = invX ? -dxRaw : dxRaw
            let dy = invY ? -dyRaw : dyRaw
            var scaledDx = dx
            var scaledDy = dy
            var didScale = false
            var consumedAndWarped = false
            if precise.isActive {
                if SystemPointerSpeed.shared.isPreciseApplied {
                    let now2 = CFAbsoluteTimeGetCurrent()
                    if now2 - lastDeltaTime > 0.08 {
                        lastDeltaTime = now2
                        DispatchQueue.main.async { [dx, dy] in
                            self.lastMouseDelta = (dx, dy, dx, dy, true)
                        }
                    }
                    return Unmanaged.passUnretained(event)
                }
                let scale = min(max(s.preciseScale, 0.10), 1.0)
                if scale < 0.99 && (dx != 0 || dy != 0) {
                    let pInvX = s.preciseInverted || s.preciseInvertedX
                    let pInvY = s.preciseInverted || s.preciseInvertedY
                    let sx = Double(dx) * scale + preciseRemainderX
                    let sy = Double(dy) * scale + preciseRemainderY
                    let outX0 = Int64(sx.rounded(.towardZero))
                    let outY0 = Int64(sy.rounded(.towardZero))
                    preciseRemainderX = sx - Double(outX0)
                    preciseRemainderY = sy - Double(outY0)
                    if abs(preciseRemainderX) > 2.0 { preciseRemainderX = 0 }
                    if abs(preciseRemainderY) > 2.0 { preciseRemainderY = 0 }
                    let adx = pInvX ? -outX0 : outX0
                    let ady = pInvY ? -outY0 : outY0
                    let cur = event.location
                    let nloc = CGPoint(x: cur.x - CGFloat(origDx) + CGFloat(adx), y: cur.y - CGFloat(origDy) + CGFloat(ady))
                    CGWarpMouseCursorPosition(nloc)
                    scaledDx = adx
                    scaledDy = ady
                    didScale = true
                    consumedAndWarped = true
                } else if dx == 0 && dy == 0 {
                    // 停止時はremainder維持
                } else {
                    preciseRemainderX = 0
                    preciseRemainderY = 0
                    let pInvX = s.preciseInverted || s.preciseInvertedX
                    let pInvY = s.preciseInverted || s.preciseInvertedY
                    if pInvX || pInvY {
                        let adx = pInvX ? -dx : dx
                        let ady = pInvY ? -dy : dy
                        let cur = event.location
                        let nloc = CGPoint(x: cur.x - CGFloat(origDx) + CGFloat(adx), y: cur.y - CGFloat(origDy) + CGFloat(ady))
                        event.location = nloc
                        event.setIntegerValueField(.mouseEventDeltaX, value: adx)
                        event.setDoubleValueField(.mouseEventDeltaX, value: Double(adx))
                        event.setIntegerValueField(.mouseEventDeltaY, value: ady)
                        event.setDoubleValueField(.mouseEventDeltaY, value: Double(ady))
                        scaledDx = adx
                        scaledDy = ady
                        didScale = true
                    } else {
                        // scale==1.0で反転なしは素通し（Warp不要）
                    }
                }
            } else {
                preciseRemainderX = 0
                preciseRemainderY = 0
                if (s.cursorInverted || s.cursorInvertedX || s.cursorInvertedY) && (origDx != 0 || origDy != 0) {
                    let cur = event.location
                    let nloc = CGPoint(x: cur.x - CGFloat(origDx) + CGFloat(dx), y: cur.y - CGFloat(origDy) + CGFloat(dy))
                    event.location = nloc
                    event.setIntegerValueField(.mouseEventDeltaX, value: dx)
                    event.setDoubleValueField(.mouseEventDeltaX, value: Double(dx))
                    event.setIntegerValueField(.mouseEventDeltaY, value: dy)
                    event.setDoubleValueField(.mouseEventDeltaY, value: Double(dy))
                    scaledDx = dx
                    scaledDy = dy
                    didScale = true
                }
            }
            let now2 = CFAbsoluteTimeGetCurrent()
            if now2 - lastDeltaTime > 0.08 {
                lastDeltaTime = now2
                DispatchQueue.main.async { [dx, dy, scaledDx, scaledDy] in
                    self.lastMouseDelta = (dx, dy, scaledDx, scaledDy, precise.isActive)
                }
            }
            if didScale, debugLogEnabled, let fh = debugLogFile {
                let pInvX = s.preciseInverted || s.preciseInvertedX
                let pInvY = s.preciseInverted || s.preciseInvertedY
                let line = String(format: "%.3f orig=%d,%d base=%d,%d -> %d,%d scale=%.2f precise=%d warped=%d pInv=%d,%d rem=%.2f,%.2f cur=%.1f,%.1f\n", now2, origDx, origDy, dx, dy, scaledDx, scaledDy, s.preciseScale, precise.isActive ? 1 : 0, consumedAndWarped ? 1 : 0, pInvX ? 1 : 0, pInvY ? 1 : 0, preciseRemainderX, preciseRemainderY, event.location.x, event.location.y)
                if let data = line.data(using: .utf8) { try? fh.write(contentsOf: data) }
            }
            if consumedAndWarped {
                return nil
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
