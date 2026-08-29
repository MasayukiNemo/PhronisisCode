import AppKit
import SwiftUI

@MainActor
final class HUDController {
    static let shared = HUDController()
    private var window: NSWindow?
    private var hideTask: Task<Void, Never>?

    func flash(active: Bool) {
        show(text: active ? "精密モード ON" : "精密モード OFF", color: active ? .systemGreen : .systemGray)
    }

    private var persistentWindow: NSWindow?

    func showPersistent(active: Bool) {
        if !active { hidePersistent(); return }
        if persistentWindow == nil {
            let w = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 180, height: 28),
                             styleMask: .borderless, backing: .buffered, defer: false)
            w.isOpaque = false
            w.backgroundColor = .clear
            w.level = .floating
            w.hasShadow = false
            w.ignoresMouseEvents = true
            w.collectionBehavior = [.canJoinAllSpaces, .stationary]
            w.isReleasedWhenClosed = false
            let label = NSTextField(labelWithString: "● 精密 ON  ●")
            label.tag = 999
            label.alignment = .center
            label.font = .systemFont(ofSize: 11, weight: .bold)
            label.textColor = .white
            let box = NSBox()
            box.boxType = .custom
            box.cornerRadius = 8
            box.fillColor = NSColor.systemGreen.withAlphaComponent(0.92)
            box.borderWidth = 0
            let container = NSView(frame: NSRect(x: 0, y: 0, width: 180, height: 28))
            label.frame = NSRect(x: 0, y: 0, width: 180, height: 28)
            label.autoresizingMask = [.width, .height]
            box.frame = container.bounds
            box.contentView = label
            container.addSubview(box)
            w.contentView = container
            persistentWindow = w
        }
        guard let w = persistentWindow, let screen = NSScreen.main else { return }
        let sf = screen.frame
        w.setFrameOrigin(NSPoint(x: sf.maxX - 200, y: sf.maxY - 40))
        w.orderFrontRegardless()
        w.alphaValue = 1.0
    }

    func hidePersistent() {
        persistentWindow?.orderOut(nil)
    }

    func show(text: String, color: NSColor) {
        if window == nil {
            let w = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 220, height: 44),
                             styleMask: .borderless, backing: .buffered, defer: false)
            w.isOpaque = false
            w.backgroundColor = .clear
            w.level = .floating
            w.hasShadow = true
            w.ignoresMouseEvents = true
            w.collectionBehavior = [.canJoinAllSpaces, .stationary]
            w.isReleasedWhenClosed = false
            self.window = w
        }
        guard let w = window else { return }
        let label = NSTextField(labelWithString: text)
        label.alignment = .center
        label.font = .systemFont(ofSize: 14, weight: .semibold)
        label.textColor = .white
        let box = NSBox()
        box.boxType = .custom
        box.cornerRadius = 10
        box.fillColor = color.withAlphaComponent(0.88)
        box.borderWidth = 0
        box.contentViewMargins = NSSize(width: 12, height: 8)
        // Center view
        let container = NSView(frame: NSRect(x: 0, y: 0, width: 220, height: 44))
        label.frame = container.bounds
        label.autoresizingMask = [.width, .height]
        box.frame = container.bounds
        box.contentView = label
        container.addSubview(box)
        w.contentView = container
        // position bottom-center
        if let screen = NSScreen.main {
            let sf = screen.frame
            w.setFrameOrigin(NSPoint(x: sf.midX - 110, y: sf.minY + 80))
        }
        w.orderFrontRegardless()
        w.alphaValue = 1.0

        hideTask?.cancel()
        hideTask = Task { @MainActor in
            try? await Task.sleep(nanoseconds: 1_200_000_000)
            NSAnimationContext.runAnimationGroup { ctx in
                ctx.duration = 0.3
                w.animator().alphaValue = 0
            } completionHandler: {
                w.orderOut(nil)
            }
        }
    }
}
