import SwiftUI

/// キーコンボをリスト選択で組み立てるビルダー（キャプチャと併用するハイブリッドの片側）
struct KeyComboBuilderView: View {
    var current: KeyCombo?
    var onChange: (KeyCombo?) -> Void

    @State private var cmd = false
    @State private var shift = false
    @State private var opt = false
    @State private var ctrl = false
    @State private var selectedKeyCode: UInt16 = 8 // C

    // 表示用のキー一覧（キャプチャできないF13等を含む）
    static let selectableKeys: [(code: UInt16, label: String)] = [
        (0, "A"), (1, "S"), (2, "D"), (3, "F"), (4, "H"), (5, "G"), (6, "Z"), (7, "X"), (8, "C"), (9, "V"),
        (11, "B"), (12, "Q"), (13, "W"), (14, "E"), (15, "R"), (16, "Y"), (17, "T"),
        (18, "1"), (19, "2"), (20, "3"), (21, "4"), (22, "6"), (23, "5"), (24, "="), (25, "9"), (26, "7"),
        (27, "-"), (28, "8"), (29, "0"), (30, "]"), (31, "O"), (32, "U"), (33, "["), (34, "I"), (35, "P"),
        (37, "L"), (38, "J"), (39, "'"), (40, "K"), (41, ";"), (42, "\\"), (43, ","), (44, "/"), (45, "N"),
        (46, "M"), (47, "."), (49, "Space"), (48, "Tab"), (51, "Delete"), (53, "Esc"), (36, "Return"), (76, "Enter"),
        (96, "F5"), (97, "F6"), (98, "F7"), (99, "F3"), (100, "F8"), (101, "F9"), (103, "F11"), (105, "F13"), (106, "F16"), (107, "F14"), (109, "F10"), (111, "F12"), (113, "F15"), (118, "F4"), (119, "F2"), (120, "F1"), (122, "F1*"),
        (123, "←"), (124, "→"), (125, "↓"), (126, "↑"),
        (102, "英数"), (104, "かな"),
    ]

    static let presets: [(name: String, combo: KeyCombo?)] = [
        ("未割り当て", nil),
        ("戻る (⌘[)", KeyCombo(keyCode: 33, modifierFlags: CGEventFlags.maskCommand.rawValue)),
        ("進む (⌘])", KeyCombo(keyCode: 30, modifierFlags: CGEventFlags.maskCommand.rawValue)),
        ("コピー (⌘C)", KeyCombo(keyCode: 8, modifierFlags: CGEventFlags.maskCommand.rawValue)),
        ("ペースト (⌘V)", KeyCombo(keyCode: 9, modifierFlags: CGEventFlags.maskCommand.rawValue)),
        ("カット (⌘X)", KeyCombo(keyCode: 7, modifierFlags: CGEventFlags.maskCommand.rawValue)),
        ("取り消し (⌘Z)", KeyCombo(keyCode: 6, modifierFlags: CGEventFlags.maskCommand.rawValue)),
        ("やり直し (⇧⌘Z)", KeyCombo(keyCode: 6, modifierFlags: CGEventFlags(arrayLiteral: .maskCommand, .maskShift).rawValue)),
        ("全選択 (⌘A)", KeyCombo(keyCode: 0, modifierFlags: CGEventFlags.maskCommand.rawValue)),
        ("検索 (⌘F)", KeyCombo(keyCode: 3, modifierFlags: CGEventFlags.maskCommand.rawValue)),
        ("タブ次 (⌃Tab)", KeyCombo(keyCode: 48, modifierFlags: CGEventFlags.maskControl.rawValue)),
        ("F13 単押し", KeyCombo(keyCode: 105, modifierFlags: 0)),
        ("F14 単押し", KeyCombo(keyCode: 107, modifierFlags: 0)),
        ("F15 単押し", KeyCombo(keyCode: 113, modifierFlags: 0)),
    ]

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                Toggle("⌘", isOn: $cmd).toggleStyle(.checkbox).onChange(of: cmd) { _ in apply() }
                Toggle("⇧", isOn: $shift).toggleStyle(.checkbox).onChange(of: shift) { _ in apply() }
                Toggle("⌥", isOn: $opt).toggleStyle(.checkbox).onChange(of: opt) { _ in apply() }
                Toggle("⌃", isOn: $ctrl).toggleStyle(.checkbox).onChange(of: ctrl) { _ in apply() }
                Picker("キー", selection: $selectedKeyCode) {
                    ForEach(Self.selectableKeys, id: \.code) { item in
                        Text(item.label).tag(item.code)
                    }
                }
                .frame(width: 130)
                .onChange(of: selectedKeyCode) { _ in apply() }
            }
            HStack(spacing: 8) {
                Menu("プリセット") {
                    ForEach(Self.presets, id: \.name) { p in
                        Button(p.name) {
                            if let c = p.combo {
                                applyPreset(c)
                            } else {
                                onChange(nil)
                                syncFromCombo(nil)
                            }
                        }
                    }
                }
                .menuStyle(.borderlessButton)
                Button("反映") { apply() }.buttonStyle(.borderedProminent).controlSize(.small)
                if current != nil {
                    Text(current?.readable ?? "").font(.caption).foregroundStyle(.secondary)
                }
            }
        }
        .padding(8)
        .background(RoundedRectangle(cornerRadius: 8).fill(Color(nsColor: .controlBackgroundColor)))
        .onAppear { syncFromCombo(current) }
        .onChange(of: current) { new in syncFromCombo(new) }
    }

    private func syncFromCombo(_ combo: KeyCombo?) {
        guard let c = combo else {
            cmd = false; shift = false; opt = false; ctrl = false
            return
        }
        let flags = CGEventFlags(rawValue: c.modifierFlags)
        cmd = flags.contains(.maskCommand)
        shift = flags.contains(.maskShift)
        opt = flags.contains(.maskAlternate)
        ctrl = flags.contains(.maskControl)
        selectedKeyCode = c.keyCode
    }

    private func apply() {
        var flags = CGEventFlags()
        if cmd { flags.insert(.maskCommand) }
        if shift { flags.insert(.maskShift) }
        if opt { flags.insert(.maskAlternate) }
        if ctrl { flags.insert(.maskControl) }
        let combo = KeyCombo(keyCode: selectedKeyCode, modifierFlags: flags.rawValue)
        onChange(combo)
    }

    private func applyPreset(_ combo: KeyCombo) {
        syncFromCombo(combo)
        onChange(combo)
    }
}
