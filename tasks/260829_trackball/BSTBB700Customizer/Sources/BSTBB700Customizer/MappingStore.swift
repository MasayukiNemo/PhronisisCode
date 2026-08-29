import Foundation
import Combine

enum ButtonID: String, Codable, CaseIterable, Sendable {
    case back = "back"           // 戻る (buttonNumber 3想定)
    case forward = "forward"     // 進む (buttonNumber 4想定)
    case center = "center"       // ホイール中央押し込み (button 2)
    case tiltLeft = "tiltLeft"
    case tiltRight = "tiltRight"
}

enum PreciseTrigger: String, Codable, CaseIterable, Sendable {
    case none = "none"
    case f13 = "f13"
    case f14 = "f14"
    case f15 = "f15"
    case capsLock = "capsLock"
    case mouseForward = "mouseForward"
    case mouseTiltRight = "mouseTiltRight"
    case mouseTiltLeft = "mouseTiltLeft"
    case mouseTiltEither = "mouseTiltEither"
    case customKey = "customKey"

    var display: String {
        switch self {
        case .none: return "なし"
        case .f13: return "F13"
        case .f14: return "F14"
        case .f15: return "F15"
        case .capsLock: return "CapsLock"
        case .mouseForward: return "進むボタン"
        case .mouseTiltRight: return "チルト右"
        case .mouseTiltLeft: return "チルト左"
        case .mouseTiltEither: return "チルト左右どちらも"
        case .customKey: return "カスタムキー（任意）"
        }
    }

    var keyCode: UInt16? {
        switch self {
        case .f13: return 105
        case .f14: return 107
        case .f15: return 113
        case .capsLock: return 57
        default: return nil
        }
    }
}

enum PreciseMode: String, Codable, Sendable {
    case toggle = "toggle"
    case hold = "hold"
}

struct AppSettings: Codable, Sendable {
    var mappings: [ButtonID: KeyCombo] = [:]
    var preciseEnabled: Bool = false
    var preciseTrigger: PreciseTrigger = .f13
    var preciseMode: PreciseMode = .toggle
    var preciseScale: Double = 0.3  // 0.1 - 1.0 デフォルト30%
    var discoveryEnabled: Bool = false
    var filterByDevice: Bool = false
    var verticalScrollPassthrough: Bool = true
    var preciseCustomKey: KeyCombo? = nil
    var tiltInverted: Bool = false
}

// 非MainActorで保持し、UI更新は手動でMainに飛ばす。EventTapコールバックはメインRunLoop上で同期実行されるためロック不要だが念のためNSLockで保護。
final class MappingStore: ObservableObject {
    static let shared = MappingStore()

    @Published var settings: AppSettings

    private let key = "bstbb700.settings.v1"

    init() {
        let loaded: AppSettings
        if let data = UserDefaults.standard.data(forKey: key),
           let decoded = try? JSONDecoder().decode(AppSettings.self, from: data) {
            loaded = decoded
        } else {
            loaded = AppSettings()
        }
        var s = loaded
        if s.preciseScale < 0.1 { s.preciseScale = 0.1 }
        if s.preciseScale > 1.0 { s.preciseScale = 1.0 }
        self.settings = s
    }

    func save() {
        if let data = try? JSONEncoder().encode(settings) {
            UserDefaults.standard.set(data, forKey: key)
        }
        if Thread.isMainThread {
            objectWillChange.send()
        } else {
            DispatchQueue.main.async { [weak self] in self?.objectWillChange.send() }
        }
    }

    func setMapping(_ combo: KeyCombo?, for button: ButtonID) {
        if let c = combo {
            settings.mappings[button] = c
        } else {
            settings.mappings.removeValue(forKey: button)
        }
        save()
    }

    func mapping(for button: ButtonID) -> KeyCombo? {
        settings.mappings[button]
    }

    var conflictMessage: String? {
        let t = settings.preciseTrigger
        if t == .mouseForward, settings.mappings[.forward] != nil {
            return "進むボタンが精密トリガーに使われているため、キー割り当てと排他です。どちらかを解除してください。"
        }
        if t == .mouseTiltRight, settings.mappings[.tiltRight] != nil {
            return "チルト右が精密トリガーに使われているため、キー割り当てと排他です。"
        }
        if t == .mouseTiltLeft, settings.mappings[.tiltLeft] != nil {
            return "チルト左が精密トリガーに使われているため、キー割り当てと排他です。"
        }
        if t == .mouseTiltEither, settings.mappings[.tiltLeft] != nil || settings.mappings[.tiltRight] != nil {
            return "チルト左右が精密トリガーに使われているため、キー割り当てと排他です。"
        }
        if t == .customKey, settings.preciseCustomKey == nil {
            return "カスタムキーが未設定です。下のキャプチャでキーを割り当ててください。"
        }
        return nil
    }

    func isPreciseTriggerConsuming(button: ButtonID) -> Bool {
        guard settings.preciseEnabled else { return false }
        switch (settings.preciseTrigger, button) {
        case (.mouseForward, .forward): return true
        case (.mouseTiltRight, .tiltRight): return true
        case (.mouseTiltLeft, .tiltLeft): return true
        case (.mouseTiltEither, .tiltLeft), (.mouseTiltEither, .tiltRight): return true
        default: return false
        }
    }

    // EventTapスレッドから高速に読むためのスナップショット（UserDefaultsキャッシュでも可だが直接読む）
    func snapshot() -> AppSettings { settings }
}
