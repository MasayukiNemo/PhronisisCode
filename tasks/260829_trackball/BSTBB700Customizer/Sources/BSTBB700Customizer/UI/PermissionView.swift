import SwiftUI
import AppKit

struct PermissionView: View {
    @State private var trusted: Bool = AXIsProcessTrusted()
    @State private var timer: Timer?

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: trusted ? "checkmark.shield.fill" : "xmark.shield.fill")
                    .foregroundStyle(trusted ? .green : .red)
                    .font(.title2)
                Text(trusted ? "権限 OK — 入力監視が許可されています" : "権限が必要です")
                    .font(.headline)
            }
            if !trusted {
                Text("「システム設定 → プライバシーとセキュリティ → 入力監視」で BSTBB700Customizer をONにしてください。\nTahoeでは再起動不要ですが、反映されない場合はアプリを再起動してください。")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                HStack(spacing: 12) {
                    Button("システム設定を開く") { openPrivacy() }
                        .buttonStyle(.borderedProminent)
                    Button("再チェック") { refresh() }
                }
            } else {
                Text("権限は正常です。進む/戻るやチルトの割り当てをお試しください。")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(12)
        .background(RoundedRectangle(cornerRadius: 10).fill(Color(nsColor: .controlBackgroundColor)))
        .onAppear { startPolling() }
        .onDisappear { timer?.invalidate() }
    }

    private func refresh() { trusted = AXIsProcessTrusted() }
    private func startPolling() {
        timer?.invalidate()
        timer = Timer.scheduledTimer(withTimeInterval: 1.5, repeats: true) { _ in
            let cur = AXIsProcessTrusted()
            DispatchQueue.main.async { trusted = cur }
        }
    }
    private func openPrivacy() {
        if let url = URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_InputMonitoring") {
            NSWorkspace.shared.open(url)
        } else {
            NSWorkspace.shared.open(URL(string: "x-apple.systempreferences:com.apple.preference.security")!)
        }
    }
}
