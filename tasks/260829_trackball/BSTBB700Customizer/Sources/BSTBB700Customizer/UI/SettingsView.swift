import SwiftUI
import ServiceManagement

struct SettingsView: View {
    @ObservedObject private var store = MappingStore.shared
    @ObservedObject private var precise = PreciseEngine.shared
    @StateObject private var discovery = HIDDiscovery()
    @State private var selectedTab = 0

    var body: some View {
        TabView(selection: $selectedTab) {
            mappingTab.tabItem { Label("割り当て", systemImage: "keyboard") }.tag(0)
            preciseTab.tabItem { Label("精密モード", systemImage: "scope") }.tag(1)
            discoveryTab.tabItem { Label("Discovery", systemImage: "antenna.radiowaves.left.and.right") }.tag(2)
            generalTab.tabItem { Label("一般", systemImage: "gear") }.tag(3)
        }
        .padding(16)
        .frame(minWidth: 640, minHeight: 700)
        .onAppear { discovery.start() }
    }

    private var mappingTab: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("BSTBB700 ボタン割り当て").font(.headline)
                Text("未割り当ては素通し（ブラウザの進む/戻る等を維持）、割り当て時は横取りしてキー送信します。チルトは水平(H)のみカスタム、垂直は素通し。").font(.caption).foregroundStyle(.secondary)

                if let msg = store.conflictMessage {
                    Label(msg, systemImage: "exclamationmark.triangle.fill").font(.caption).foregroundStyle(.orange)
                        .padding(8).background(RoundedRectangle(cornerRadius: 8).fill(Color.orange.opacity(0.15)))
                }

                PermissionView()

                VStack(spacing: 10) {
                    HybridKeyRow(title: "戻る", current: store.mapping(for: .back)) { c in store.setMapping(c, for: .back) }
                    HybridKeyRow(title: "進む", current: store.mapping(for: .forward)) { c in store.setMapping(c, for: .forward) }
                    HybridKeyRow(title: "中央押し", current: store.mapping(for: .center)) { c in store.setMapping(c, for: .center) }
                    Divider()
                    HybridKeyRow(title: "チルト左", current: store.mapping(for: .tiltLeft)) { c in store.setMapping(c, for: .tiltLeft) }
                    HybridKeyRow(title: "チルト右", current: store.mapping(for: .tiltRight)) { c in store.setMapping(c, for: .tiltRight) }
                }
                .padding(12)
                .background(RoundedRectangle(cornerRadius: 10).fill(Color(nsColor: .controlBackgroundColor)))
            }
            .padding(.top, 8)
            .padding(.horizontal, 4)
        }
    }

    private var preciseTab: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("精密モード").font(.headline)
                Toggle("精密モードを有効化", isOn: Binding(get: { store.settings.preciseEnabled }, set: { v in
                    store.settings.preciseEnabled = v
                    store.save()
                }))
                .toggleStyle(.switch)

                HStack {
                    Text("トリガー").frame(width: 80, alignment: .leading)
                    Picker("", selection: Binding(get: { store.settings.preciseTrigger }, set: { v in
                        store.settings.preciseTrigger = v; store.save()
                        if v == .mouseTiltRight, store.settings.preciseMode == .hold {
                            store.settings.preciseMode = .toggle
                            store.save()
                        }
                    })) {
                        ForEach(PreciseTrigger.allCases, id: \.self) { t in Text(t.display).tag(t) }
                    }.labelsHidden().frame(width: 200)
                }
                if store.settings.preciseTrigger == .customKey {
                    VStack(alignment: .leading, spacing: 6) {
                        HybridKeyRow(title: "カスタムキー", current: store.settings.preciseCustomKey) { c in
                            store.settings.preciseCustomKey = c
                            store.save()
                        }
                        Text("カスタムキーは修飾なしの単押しを推奨。§キー、英数、右⌥等、押せる未使用キーをキャプチャまたはリスト選択で割り当て。").font(.caption2).foregroundStyle(.secondary)
                    }
                }
                HStack {
                    Text("モード").frame(width: 80, alignment: .leading)
                    Picker("", selection: Binding(get: { store.settings.preciseMode }, set: { v in
                        store.settings.preciseMode = v; store.save()
                    })) {
                        Text("トグル（押すたびON/OFF）").tag(PreciseMode.toggle)
                        Text("ホールド（押している間のみ）").tag(PreciseMode.hold)
                    }.labelsHidden().pickerStyle(.radioGroup)
                    .disabled(store.settings.preciseTrigger == .mouseTiltRight && store.settings.preciseMode == .hold)
                }
                if store.settings.preciseTrigger == .mouseTiltRight {
                    Label("チルト右はホールド非対応（離上イベントがないため）。トグルのみ推奨。", systemImage: "info.circle").font(.caption2).foregroundStyle(.orange)
                }
                if store.settings.preciseTrigger == .capsLock {
                    Label("CapsLockはflagsChangedで判定します。システムのCapsLock動作と競合する場合があります。", systemImage: "info.circle").font(.caption2).foregroundStyle(.secondary)
                }

                VStack(alignment: .leading, spacing: 6) {
                    HStack {
                        Text("移動量スケール")
                        Spacer()
                        Text("\(Int(store.settings.preciseScale * 100))%").monospacedDigit().foregroundStyle(.secondary)
                    }
                    Slider(value: Binding(get: { store.settings.preciseScale }, set: { v in
                        store.settings.preciseScale = min(max(v, 0.1), 1.0)
                        store.save()
                    }), in: 0.1...1.0, step: 0.05)
                    HStack { Text("10%").font(.caption2).foregroundStyle(.secondary); Spacer(); Text("100%").font(.caption2).foregroundStyle(.secondary) }
                }

                HStack(spacing: 8) {
                    Circle().fill(precise.isActive ? Color.green : Color.gray).frame(width: 12, height: 12)
                    Text(precise.isActive ? "精密 ON（減速中）" : "精密 OFF").font(.caption).foregroundStyle(precise.isActive ? .green : .secondary)
                    Spacer()
                    Button(precise.isActive ? "OFFにする" : "ONにする") { precise.toggle() }
                        .disabled(!store.settings.preciseEnabled || store.settings.preciseMode != .toggle)
                }
                .padding(8).background(RoundedRectangle(cornerRadius: 8).fill(Color(nsColor: .controlBackgroundColor)))

                Label("注意: MVPでは精密モードはグローバル減速です。トラックパッドや他マウスも減速します。将来的にBSTBB700のみに限定するフィルタを追加予定。", systemImage: "info.circle")
                    .font(.caption).foregroundStyle(.secondary)

                if let msg = store.conflictMessage {
                    Label(msg, systemImage: "exclamationmark.triangle").font(.caption).foregroundStyle(.orange)
                }
            }
            .padding(.top, 8)
            .padding(.horizontal, 4)
        }
    }

    private var discoveryTab: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Discovery ログモード").font(.headline)
            Text("BSTBB700のBluetooth接続でボタンを押すと、ButtonID / scrollWheel axis / keyCode がログに出ます。VID/PID特定用。").font(.caption).foregroundStyle(.secondary)
            Toggle("ログを有効化", isOn: Binding(get: { store.settings.discoveryEnabled }, set: { v in store.settings.discoveryEnabled = v; store.save() }))
                .toggleStyle(.switch)
            HStack {
                Button("クリア") { discovery.clear() }
                Spacer()
                Text("\(discovery.logLines.count) lines").font(.caption).foregroundStyle(.secondary)
            }
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 2) {
                    ForEach(Array(discovery.logLines.suffix(300)), id: \.self) { line in
                        Text(line).font(.system(.caption, design: .monospaced)).textSelection(.enabled)
                    }
                }
            }
            .frame(minHeight: 200).padding(8).background(RoundedRectangle(cornerRadius: 8).fill(Color(nsColor: .textBackgroundColor))).overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.gray.opacity(0.2)))

            Text("検出デバイス").font(.subheadline)
            ForEach(discovery.devices.prefix(8), id: \.id) { d in
                HStack {
                    Text(d.product).font(.caption)
                    Spacer()
                    Text("VID:\(d.vendorID.map(String.init) ?? "-") PID:\(d.productID.map(String.init) ?? "-") \(d.transport ?? "")").font(.caption2).foregroundStyle(.secondary)
                }
            }
            Spacer()
        }
        .padding(.top, 8)
    }

    private var generalTab: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("一般").font(.headline)
            LoginItemToggle()
            Divider()
            VStack(alignment: .leading, spacing: 6) {
                Text("配布と署名").font(.subheadline)
                Text("ad-hoc署名で動作します。Gatekeeperでブロックされた場合は `xattr -cr BSTBB700Customizer.app` 後に右クリック→開くで起動してください。SandboxはOFF。\nシステム設定 > プライバシーとセキュリティ > 入力監視 / アクセシビリティ で本アプリを許可してください。").font(.caption).foregroundStyle(.secondary)
                Text("BundleID: com.buffalo.bstbb700.customizer").font(.caption2).foregroundStyle(.secondary).textSelection(.enabled)
            }
            VStack(alignment: .leading, spacing: 6) {
                Text("バージョン").font(.subheadline)
                Text("BSTBB700 Customizer 0.1.0 (MVP) — Swift 6.3 / macOS 13+ / Universal").font(.caption).foregroundStyle(.secondary)
            }
            Spacer()
        }
        .padding(.top, 8)
    }
}

/// キャプチャとリスト選択のハイブリッド行（ELECOM/Logitech/Keychronパターンを統合）
struct HybridKeyRow: View {
    var title: String
    var current: KeyCombo?
    var onChange: (KeyCombo?) -> Void
    @State private var showBuilder = false
    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            KeyCaptureView(title: title, current: current, onCapture: onChange)
            DisclosureGroup(isExpanded: $showBuilder) {
                KeyComboBuilderView(current: current, onChange: onChange)
            } label: {
                Text("リスト選択で組み立て（押しにくいキー・複合キー用）").font(.caption2).foregroundStyle(.secondary)
            }
        }
        .padding(6)
        .background(RoundedRectangle(cornerRadius: 6).fill(Color(nsColor: .windowBackgroundColor)))
        .overlay(RoundedRectangle(cornerRadius: 6).stroke(Color.gray.opacity(0.15)))
    }
}

struct LoginItemToggle: View {
    @State private var enabled: Bool = false
    @State private var errorMsg: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Toggle("ログイン時に自動起動", isOn: $enabled)
                .toggleStyle(.switch)
                .onChange(of: enabled) { new in setLoginItem(enabled: new) }
            if let e = errorMsg { Text(e).font(.caption).foregroundStyle(.red) }
            Text("SMAppService loginItem で登録します。").font(.caption).foregroundStyle(.secondary)
        }
        .onAppear { refresh() }
    }
    private func refresh() {
        if #available(macOS 13.0, *) {
            enabled = SMAppService.mainApp.status == .enabled
        }
    }
    private func setLoginItem(enabled: Bool) {
        if #available(macOS 13.0, *) {
            do {
                if enabled { try SMAppService.mainApp.register() } else { try SMAppService.mainApp.unregister() }
                errorMsg = nil
            } catch {
                errorMsg = "登録失敗: \(error.localizedDescription)"
                refresh()
            }
        }
    }
}
