import SwiftUI
import AppKit
import Carbon

struct KeyCaptureView: View {
    var title: String
    var current: KeyCombo?
    var onCapture: (KeyCombo?) -> Void

    @State private var isCapturing = false
    @State private var capturedText = ""

    var body: some View {
        HStack {
            Text(title).frame(width: 110, alignment: .leading)
            if isCapturing {
                Text("キーコンボを押してください… (Escでキャンセル)").font(.caption).foregroundStyle(.orange)
            } else {
                Text(current?.readable ?? "未割り当て").foregroundStyle(current == nil ? .secondary : .primary)
                    .frame(minWidth: 120, alignment: .leading)
            }
            Spacer()
            Button(isCapturing ? "キャンセル" : (current == nil ? "割り当て" : "変更")) {
                isCapturing.toggle()
                if isCapturing { capturedText = "" }
            }.buttonStyle(.bordered)
            if current != nil && !isCapturing {
                Button("クリア") { onCapture(nil) }.buttonStyle(.bordered)
            }
        }
        .background(
            KeyCaptureNSView(isCapturing: $isCapturing) { combo in
                onCapture(combo)
                isCapturing = false
            }
        )
    }
}

/// 裏側でキーイベントを拾うNSViewラッパ
struct KeyCaptureNSView: NSViewRepresentable {
    @Binding var isCapturing: Bool
    var onCaptured: (KeyCombo) -> Void

    func makeNSView(context: Context) -> CaptureView {
        let v = CaptureView()
        v.onCaptured = onCaptured
        return v
    }
    func updateNSView(_ nsView: CaptureView, context: Context) {
        nsView.isCapturing = isCapturing
        nsView.onCaptured = onCaptured
    }

    final class CaptureView: NSView {
        var isCapturing = false
        var onCaptured: ((KeyCombo) -> Void)?

        override var acceptsFirstResponder: Bool { true }

        override func viewDidMoveToWindow() {
            super.viewDidMoveToWindow()
            window?.makeFirstResponder(self)
        }

        override func keyDown(with event: NSEvent) {
            guard isCapturing else { super.keyDown(with: event); return }
            if event.keyCode == 53 { // Esc
                // キャンセルは親が isCapturing=false にする。ここでは何も送らない
                return
            }
            let flags = event.modifierFlags.intersection([.command, .shift, .option, .control])
            let cgFlags = KeyCombo.cgFlags(from: flags)
            let combo = KeyCombo(keyCode: UInt16(event.keyCode), modifierFlags: cgFlags.rawValue)
            onCaptured?(combo)
        }

        override func flagsChanged(with event: NSEvent) {
            // 修飾のみは無視
            super.flagsChanged(with: event)
        }
    }
}
