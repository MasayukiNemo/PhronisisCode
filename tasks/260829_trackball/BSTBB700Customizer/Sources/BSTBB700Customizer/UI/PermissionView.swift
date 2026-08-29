import SwiftUI
import AppKit

struct PermissionView: View {
    @State private var axTrusted: Bool = AXIsProcessTrusted()
    @State private var listenOK: Bool = {
        if #available(macOS 10.15, *) { return CGPreflightListenEventAccess() } else { return true }
    }()
    @State private var postOK: Bool = {
        if #available(macOS 10.15, *) { return CGPreflightPostEventAccess() } else { return true }
    }()
    @State private var timer: Timer?

    private var allOK: Bool { axTrusted && listenOK && postOK }
    private var tapRunning: Bool { EventTapManager.shared.isRunning }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: allOK && tapRunning ? "checkmark.shield.fill" : "xmark.shield.fill")
                    .foregroundStyle(allOK && tapRunning ? .green : .red)
                    .font(.title2)
                Text(allOK && tapRunning ? "権限 OK — 入力監視が許可されています" : "権限が必要です")
                    .font(.headline)
            }
            if !(allOK && tapRunning) {
                VStack(alignment: .leading, spacing: 4) {
                    Label(axTrusted ? "✓ アクセシビリティ: 許可" : "✗ アクセシビリティ: 未許可", systemImage: axTrusted ? "checkmark.circle.fill" : "xmark.circle.fill")
                        .font(.caption).foregroundStyle(axTrusted ? .green : .orange)
                    Label(listenOK ? "✓ 入力監視 (Listen): 許可" : "✗ 入力監視 (Listen): 未許可 — CGEventTapに必須", systemImage: listenOK ? "checkmark.circle.fill" : "xmark.circle.fill")
                        .font(.caption).foregroundStyle(listenOK ? .green : .red)
                    Label(postOK ? "✓ イベント送信 (Post): 許可" : "✗ イベント送信 (Post): 未許可 — キー送信に必須", systemImage: postOK ? "checkmark.circle.fill" : "xmark.circle.fill")
                        .font(.caption).foregroundStyle(postOK ? .green : .orange)
                    if !tapRunning {
                        Label("EventTap未起動", systemImage: "exclamationmark.triangle.fill").font(.caption).foregroundStyle(.orange)
                    }
                }
                Text("「システム設定 → プライバシーとセキュリティ → 入力監視」で BSTBB700Customizer をONにしてください。\n「アクセシビリティ」もONが必要です。\nListen=ボタン横取りに必須 / Post=キー送信に必須 / AX=旧API互換。\n「許可を要求」は初回のみダイアログが出ます。拒否後は設定で手動ONしてください。許可後は自動で反映されますが、反映されない場合は「再チェック」またはアプリ再起動してください。")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                HStack(spacing: 12) {
                    Button("入力監視を開く") { openPrivacyPane("Privacy_InputMonitoring") }
                        .buttonStyle(.borderedProminent)
                    Button("アクセシビリティを開く") { openPrivacyPane("Privacy_Accessibility") }
                        .buttonStyle(.bordered)
                    Button("再チェック") { refreshAndRestartIfNeeded() }
                }
                if !listenOK {
                    Button("入力監視の許可を要求") {
                        if #available(macOS 10.15, *) { _ = CGRequestListenEventAccess() }
                        refreshAndRestartIfNeeded()
                    }.font(.caption)
                }
                if !postOK {
                    Button("イベント送信の許可を要求") {
                        if #available(macOS 10.15, *) { _ = CGRequestPostEventAccess() }
                        refreshAndRestartIfNeeded()
                    }.font(.caption)
                }
            } else {
                Text("権限は正常です。EventTap動作中。進む/戻るやチルトの割り当てをお試しください。")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(12)
        .background(RoundedRectangle(cornerRadius: 10).fill(Color(nsColor: .controlBackgroundColor)))
        .onAppear { startPolling() }
        .onDisappear { timer?.invalidate() }
    }

    private func refresh() {
        axTrusted = AXIsProcessTrusted()
        if #available(macOS 10.15, *) {
            listenOK = CGPreflightListenEventAccess()
            postOK = CGPreflightPostEventAccess()
        }
    }

    private func refreshAndRestartIfNeeded() {
        refresh()
        if EventTapManager.shared.canStartTap() && !EventTapManager.shared.isRunning {
            DispatchQueue.main.async { EventTapManager.shared.start() }
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) { refresh() }
        } else if allOK && !EventTapManager.shared.isRunning {
            DispatchQueue.main.async { EventTapManager.shared.start() }
        }
    }

    private func startPolling() {
        timer?.invalidate()
        refresh()
        if EventTapManager.shared.canStartTap() && !EventTapManager.shared.isRunning {
            DispatchQueue.main.async { EventTapManager.shared.start() }
        }
        timer = Timer.scheduledTimer(withTimeInterval: 1.5, repeats: true) { _ in
            DispatchQueue.main.async {
                self.refresh()
                if EventTapManager.shared.canStartTap() && !EventTapManager.shared.isRunning {
                    EventTapManager.shared.start()
                }
            }
        }
    }
    private func openPrivacyPane(_ pane: String) {
        if let url = URL(string: "x-apple.systempreferences:com.apple.preference.security?\(pane)") {
            NSWorkspace.shared.open(url)
        } else {
            NSWorkspace.shared.open(URL(string: "x-apple.systempreferences:com.apple.preference.security")!)
        }
        // フォールバック: 手動で開く案内
        if pane == "Privacy_InputMonitoring" {
            NSLog("[BSTBB700] Open InputMonitoring pane")
        }
    }
}
