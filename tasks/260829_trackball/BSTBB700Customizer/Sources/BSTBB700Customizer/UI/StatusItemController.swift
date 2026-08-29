import AppKit
import SwiftUI
import Combine

@MainActor
final class StatusItemController: ObservableObject {
    private var statusItem: NSStatusItem?
    private var cancellables = Set<AnyCancellable>()

    func setup() {
        let item = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        self.statusItem = item

        updateIcon(isPrecise: PreciseEngine.shared.isActive)

        PreciseEngine.shared.$isActive.sink { [weak self] active in
            self?.updateIcon(isPrecise: active)
        }.store(in: &cancellables)

        if let button = item.button {
            button.image = NSImage(systemSymbolName: "scope", accessibilityDescription: "BSTBB700")
            button.target = self
            button.action = #selector(handleClick(_:))
            button.sendAction(on: [.leftMouseUp, .rightMouseUp])
        }

        let menu = NSMenu()
        menu.addItem(NSMenuItem(title: "設定を開く…", action: #selector(openSettings), keyEquivalent: ","))
        menu.addItem(NSMenuItem.separator())
        let preciseItem = NSMenuItem(title: "精密モード", action: nil, keyEquivalent: "")
        preciseItem.view = nil
        menu.addItem(preciseItem)
        menu.addItem(NSMenuItem(title: "精密 ON/OFF 切替", action: #selector(togglePrecise), keyEquivalent: ""))
        menu.addItem(NSMenuItem.separator())
        menu.addItem(NSMenuItem(title: "終了", action: #selector(quit), keyEquivalent: "q"))
        item.menu = menu
    }

    private func updateIcon(isPrecise: Bool) {
        guard let button = statusItem?.button else { return }
        button.image = NSImage(systemSymbolName: isPrecise ? "scope" : "circle.dotted.scope",
                               accessibilityDescription: isPrecise ? "Precise ON" : "Precise OFF")
        button.contentTintColor = isPrecise ? .systemGreen : nil
    }

    @objc private func handleClick(_ sender: Any?) {
        guard let event = NSApp.currentEvent else { return }
        if event.type == .rightMouseUp {
            statusItem?.menu?.popUp(positioning: nil, at: NSPoint(x: 0, y: (statusItem?.button?.bounds.height ?? 0)), in: statusItem?.button)
        } else {
            openSettings()
        }
    }

    @objc private func openSettings() {
        SettingsWindowController.shared.show()
    }

    @objc private func togglePrecise() {
        let store = MappingStore.shared
        guard store.settings.preciseEnabled else { return }
        PreciseEngine.shared.toggle()
    }

    @objc private func quit() {
        NSApp.terminate(nil)
    }
}
