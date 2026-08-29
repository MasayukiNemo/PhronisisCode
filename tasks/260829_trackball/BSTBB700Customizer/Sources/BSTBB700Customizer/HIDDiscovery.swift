import Foundation
import IOKit
import IOKit.hid
import CoreGraphics

/// IOHIDManagerでデバイス列挙 + CGEventTapログを統合するDiscovery。
/// BSTBB700のVID/PID/Transport と、ボタンがどのUsageで届くかを特定する。
final class HIDDiscovery: ObservableObject {
    @Published var logLines: [String] = []
    @Published var devices: [HIDDeviceInfo] = []

    struct HIDDeviceInfo: Identifiable {
        var id: String
        var product: String
        var vendorID: Int?
        var productID: Int?
        var transport: String?
        var usagePage: Int?
        var usage: Int?
    }

    private var manager: IOHIDManager?

    func start() {
        enumerate()
    }

    func enumerate() {
        let mgr = IOHIDManagerCreate(kCFAllocatorDefault, IOOptionBits(kIOHIDOptionsTypeNone))
        // 全デバイス取得（フィルタなし）
        IOHIDManagerSetDeviceMatching(mgr, nil)
        IOHIDManagerScheduleWithRunLoop(mgr, CFRunLoopGetMain(), CFRunLoopMode.defaultMode.rawValue)
        let res = IOHIDManagerOpen(mgr, IOOptionBits(kIOHIDOptionsTypeNone))
        if res != kIOReturnSuccess {
            append("IOHIDManagerOpen failed: \(res)")
        }
        self.manager = mgr

        guard let set = IOHIDManagerCopyDevices(mgr) as? Set<IOHIDDevice> else {
            append("No HID devices found")
            return
        }
        var infos: [HIDDeviceInfo] = []
        for dev in set {
            let product = (IOHIDDeviceGetProperty(dev, kIOHIDProductKey as CFString) as? String) ?? "Unknown"
            let vid = IOHIDDeviceGetProperty(dev, kIOHIDVendorIDKey as CFString) as? Int
            let pid = IOHIDDeviceGetProperty(dev, kIOHIDProductIDKey as CFString) as? Int
            let transport = IOHIDDeviceGetProperty(dev, kIOHIDTransportKey as CFString) as? String
            let up = IOHIDDeviceGetProperty(dev, kIOHIDPrimaryUsagePageKey as CFString) as? Int
            let u = IOHIDDeviceGetProperty(dev, kIOHIDPrimaryUsageKey as CFString) as? Int
            let uid = "\(vid ?? 0):\(pid ?? 0):\(product):\(transport ?? "-"):\(up ?? -1):\(u ?? -1)"
            let info = HIDDeviceInfo(id: uid, product: product, vendorID: vid, productID: pid, transport: transport, usagePage: up, usage: u)
            infos.append(info)
        }
        // Bluetooth優先ソート
        infos.sort { a, b in
            let aBT = a.transport == "Bluetooth"
            let bBT = b.transport == "Bluetooth"
            if aBT != bBT { return aBT && !bBT }
            return (a.product) < (b.product)
        }
        self.devices = infos
        append("Enumerated \(infos.count) HID devices")
        for i in infos.prefix(20) {
            append("Device: \(i.product) VID:\(i.vendorID?.description ?? "-") PID:\(i.productID?.description ?? "-") transport:\(i.transport ?? "-") up:\(i.usagePage?.description ?? "-") u:\(i.usage?.description ?? "-")")
        }
    }

    func append(_ line: String) {
        let ts = ISO8601DateFormatter().string(from: Date())
        let entry = "[\(ts)] \(line)"
        DispatchQueue.main.async { [weak self] in
            self?.logLines.append(entry)
            if (self?.logLines.count ?? 0) > 500 {
                self?.logLines.removeFirst(100)
            }
        }
        NSLog("[BSTBB700 Discovery] %@", line)
    }

    func clear() {
        logLines.removeAll()
    }

    func stop() {
        if let m = manager {
            IOHIDManagerClose(m, IOOptionBits(kIOHIDOptionsTypeNone))
            IOHIDManagerUnscheduleFromRunLoop(m, CFRunLoopGetMain(), CFRunLoopMode.defaultMode.rawValue)
        }
        manager = nil
    }
}
