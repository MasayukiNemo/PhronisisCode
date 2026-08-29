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
            // SF SymbolsはOSバージョンで存在しない場合があるためフォールバックを用意
            let img = NSImage(systemSymbolName: "scope", accessibilityDescription: "BSTBB700")
                ?? NSImage(systemSymbolName: "target", accessibilityDescription: "BSTBB700")
            button.image = img
            button.imagePosition = .imageOnly
            // isVisibleはmacOS 13+で非表示にされることがあるため明示
            if #available(macOS 13.0, *) {
                item.isVisible = true
            }
            NSLog("[BSTBB700] StatusItem button created: image=%@ frame=%@", String(describing: button.image), NSStringFromRect(button.frame))
        } else {
            NSLog("[BSTBB700] ERROR: statusItem.button is nil - menu bar may be hidden or system limit")
        }

        let menu = NSMenu()
        menu.autoenablesItems = false
        let openItem = NSMenuItem(title: "設定を開く…", action: #selector(openSettings), keyEquivalent: ",")
        openItem.target = self
        openItem.isEnabled = true
        menu.addItem(openItem)
        menu.addItem(NSMenuItem.separator())
        let preciseItem = NSMenuItem(title: "精密モード", action: nil, keyEquivalent: "")
        preciseItem.isEnabled = false
        menu.addItem(preciseItem)
        let toggleItem = NSMenuItem(title: "精密 ON/OFF 切替", action: #selector(togglePrecise), keyEquivalent: "")
        toggleItem.target = self
        toggleItem.isEnabled = true
        menu.addItem(toggleItem)
        menu.addItem(NSMenuItem.separator())
        let quitItem = NSMenuItem(title: "終了", action: #selector(quit), keyEquivalent: "q")
        quitItem.target = self
        quitItem.isEnabled = true
        menu.addItem(quitItem)
        item.menu = menu
        if #available(macOS 13.0, *) {
            NSLog("[BSTBB700] StatusItem menu set, isVisible=%d", item.isVisible ? 1 : 0)
        } else {
            NSLog("[BSTBB700] StatusItem menu set")
        }
    }

    private func updateIcon(isPrecise: Bool) {
        guard let button = statusItem?.button else {
            NSLog("[BSTBB700] updateIcon failed: button is nil")
            return
        }
        // "circle.dotted.scope"はmacOS 14+でしか存在しないためフォールバック
        let name = isPrecise ? "scope" : "scope"
        let fallback = isPrecise ? "target" : "circle"
        let img = NSImage(systemSymbolName: name, accessibilityDescription: isPrecise ? "Precise ON" : "Precise OFF")
            ?? NSImage(systemSymbolName: fallback, accessibilityDescription: "BSTBB700")
        button.image = img
        button.contentTintColor = isPrecise ? .systemGreen : nil
        if #available(macOS 13.0, *) {
            statusItem?.isVisible = true
        }
        NSLog("[BSTBB700] updateIcon isPrecise=%@ image=%@", isPrecise ? "ON" : "OFF", String(describing: img))
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
