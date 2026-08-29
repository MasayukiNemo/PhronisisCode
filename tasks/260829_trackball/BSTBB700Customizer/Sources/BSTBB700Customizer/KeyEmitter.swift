import CoreGraphics
import AppKit

enum KeyEmitter {
    private static let emitMagic: Int64 = 0xB700B700
    private static var emitSource: CGEventSource? = {
        let s = CGEventSource(stateID: .hidSystemState)
        s?.localEventsSuppressionInterval = 0
        return s
    }()

    /// KeyComboをグローバルに送信。自己生成タグを付与し再帰を防止。
    static func emit(combo: KeyCombo) {
        let flags = CGEventFlags(rawValue: combo.modifierFlags)
        let keyCode = CGKeyCode(combo.keyCode)

        if #available(macOS 14.0, *) {
            if !CGPreflightPostEventAccess() {
                NSLog("[BSTBB700] KeyEmitter: PostEvent access denied, please grant Input Monitoring")
                return
            }
        }

        guard let down = CGEvent(keyboardEventSource: emitSource, virtualKey: keyCode, keyDown: true),
              let up = CGEvent(keyboardEventSource: emitSource, virtualKey: keyCode, keyDown: false) else {
            NSLog("[BSTBB700] KeyEmitter: failed to create keyboard event keyCode=\(keyCode)")
            return
        }
        down.flags = flags
        up.flags = flags
        down.setIntegerValueField(.eventSourceUserData, value: emitMagic)
        up.setIntegerValueField(.eventSourceUserData, value: emitMagic)
        down.post(tap: .cghidEventTap)
        up.post(tap: .cghidEventTap)
        NSLog("[BSTBB700] emitted \(combo.readable) keyCode=\(keyCode) flags=\(flags.rawValue)")
    }

    /// 単一キー押下/解放を個別post（精密トリガーのホールド判定等では使わないが、将来用）
    static func postKey(keyCode: UInt16, flags: CGEventFlags, down: Bool) {
        guard let ev = CGEvent(keyboardEventSource: nil, virtualKey: CGKeyCode(keyCode), keyDown: down) else { return }
        ev.flags = flags
        ev.post(tap: .cghidEventTap)
    }
}
