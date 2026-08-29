import CoreGraphics
import AppKit

enum KeyEmitter {
    /// KeyComboをグローバルに送信。修飾キーはflagsで付与し、keyDown/keyUpを順にpost。
    static func emit(combo: KeyCombo) {
        let flags = CGEventFlags(rawValue: combo.modifierFlags)
        let keyCode = CGKeyCode(combo.keyCode)

        // 権限チェック (macOS 14+): CGPreflightPostEventAccessがあれば使う
        if #available(macOS 14.0, *) {
            if !CGPreflightPostEventAccess() {
                NSLog("[BSTBB700] KeyEmitter: PostEvent access denied, please grant Input Monitoring")
                return
            }
        }

        guard let down = CGEvent(keyboardEventSource: nil, virtualKey: keyCode, keyDown: true),
              let up = CGEvent(keyboardEventSource: nil, virtualKey: keyCode, keyDown: false) else {
            NSLog("[BSTBB700] KeyEmitter: failed to create keyboard event keyCode=\(keyCode)")
            return
        }
        down.flags = flags
        up.flags = flags
        // TAPは hidEventTap
        down.post(tap: .cghidEventTap)
        // 少し待つと修飾が確実に届く（連続送信時の取りこぼし防止）
        // usleep 1000 は使わず、即時postでOK。必要なら遅延を入れる。
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
