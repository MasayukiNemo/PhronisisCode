import Foundation
import CoreGraphics
import Combine

final class PreciseEngine: ObservableObject {
    static let shared = PreciseEngine()

    @Published var isActive: Bool = false
    @Published var isHoldPressed: Bool = false
    private let lock = NSLock()

    private var store: MappingStore { MappingStore.shared }

    var scale: Double {
        let s = store.settings.preciseScale
        return min(max(s, 0.1), 1.0)
    }

    func toggle() {
        guard store.settings.preciseEnabled else { return }
        guard store.settings.preciseMode == .toggle else { return }
        isActive.toggle()
        DispatchQueue.main.async { HUDController.shared.flash(active: self.isActive) }
    }

    func holdBegan() {
        guard store.settings.preciseEnabled else { return }
        guard store.settings.preciseMode == .hold else { return }
        isHoldPressed = true
        isActive = true
        DispatchQueue.main.async { HUDController.shared.flash(active: true) }
    }

    func holdEnded() {
        guard store.settings.preciseMode == .hold else { return }
        isHoldPressed = false
        isActive = false
        DispatchQueue.main.async { HUDController.shared.flash(active: false) }
    }

    func handleKeyboardTrigger(keyCode: UInt16, isDown: Bool) -> Bool {
        guard store.settings.preciseEnabled else { return false }
        let settings = store.settings
        // カスタムキー優先
        if settings.preciseTrigger == .customKey, let custom = settings.preciseCustomKey {
            guard custom.keyCode == keyCode else { return false }
            // 修飾も一致が必要（CapsLock等はflagsで判定するケースもあるため、modifier一致を要求）
            // MVPはkeyCode一致のみで判定し、modifierは無視（任意の未使用キーを想定）
            switch settings.preciseMode {
            case .toggle:
                if isDown { toggle() }
                return true
            case .hold:
                if isDown { holdBegan() } else { holdEnded() }
                return true
            }
        }
        guard let triggerCode = settings.preciseTrigger.keyCode else { return false }
        guard triggerCode == keyCode else { return false }

        switch settings.preciseMode {
        case .toggle:
            if isDown { toggle() }
            return true
        case .hold:
            if isDown { holdBegan() } else { holdEnded() }
            return true
        }
    }

    func handleMouseTrigger(button: ButtonID, isDown: Bool) -> Bool {
        guard store.settings.preciseEnabled else { return false }
        let t = store.settings.preciseTrigger
        let matches: Bool = (t == .mouseForward && button == .forward) || (t == .mouseTiltRight && button == .tiltRight)
        guard matches else { return false }
        // チルト右はscrollWheelでupが取れないためholdは不可。toggleにフォールバック
        if button == .tiltRight, store.settings.preciseMode == .hold {
            // hold要求だがチルトでは離上イベントがないためtoggleとして扱う
            if isDown { toggle() }
            return true
        }
        switch store.settings.preciseMode {
        case .toggle:
            if isDown { toggle() }
            return true
        case .hold:
            if isDown { holdBegan() } else { holdEnded() }
            return true
        }
    }

    func handleCapsLockFlagsChanged(event: CGEvent) -> Bool {
        guard store.settings.preciseEnabled else { return false }
        guard store.settings.preciseTrigger == .capsLock else { return false }
        // flagsChangedではkeyDown/upが区別しにくいため、トグルは押下とみなす
        // holdモードではflagsにalphaShiftが含まれていればON、なければOFF
        switch store.settings.preciseMode {
        case .toggle:
            // 1回のflagsChangedで1回トグル（連打抑止は呼び出し側でデバウンスなし）
            toggle()
            return true
        case .hold:
            let isOn = event.flags.contains(.maskAlphaShift)
            if isOn { holdBegan() } else { holdEnded() }
            return true
        }
    }

    func scaledDeltas(for event: CGEvent) -> (dx: Double, dy: Double) {
        let dx = event.getDoubleValueField(.mouseEventDeltaX)
        let dy = event.getDoubleValueField(.mouseEventDeltaY)
        if isActive {
            return (dx * scale, dy * scale)
        }
        return (dx, dy)
    }

    func applyScale(to event: CGEvent) {
        guard isActive else { return }
        let (ndx, ndy) = scaledDeltas(for: event)
        event.setDoubleValueField(.mouseEventDeltaX, value: ndx)
        event.setDoubleValueField(.mouseEventDeltaY, value: ndy)
    }
}
