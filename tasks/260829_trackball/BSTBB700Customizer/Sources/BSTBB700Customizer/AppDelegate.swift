import AppKit
import SwiftUI
import Combine

@MainActor
final class AppDelegate: NSObject, NSApplicationDelegate {
    var statusController: StatusItemController?
    var eventTap: EventTapManager { EventTapManager.shared }
    var discovery = HIDDiscovery()

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory) // LSUIElement相当、Dockに出さない常駐
        setupStatusItem()
        discovery.start()
        eventTap.setDiscovery(discovery)
        // 権限があれば自動開始、なければPermissionViewで誘導
        if eventTap.checkAccessibility() {
            eventTap.start()
        } else {
            NSLog("[BSTBB700] Needs Input Monitoring permission — showing settings")
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.8) {
                SettingsWindowController.shared.show()
            }
        }
        // 精密HUD監視
        observePrecise()
    }

    func applicationWillTerminate(_ notification: Notification) {
        eventTap.stop()
        discovery.stop()
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { false }

    private func setupStatusItem() {
        let c = StatusItemController()
        c.setup()
        self.statusController = c
    }

    private var cancellables = Set<AnyCancellable>()
    private func observePrecise() {
        // 追加の監視があればここに
    }
}
