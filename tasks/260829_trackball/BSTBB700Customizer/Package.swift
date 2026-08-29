// swift-tools-version: 5.10
import PackageDescription

let package = Package(
    name: "BSTBB700Customizer",
    platforms: [
        .macOS(.v13)
    ],
    products: [
        .executable(name: "BSTBB700Customizer", targets: ["BSTBB700Customizer"])
    ],
    targets: [
        .executableTarget(
            name: "BSTBB700Customizer",
            path: "Sources/BSTBB700Customizer",
            linkerSettings: [
                .linkedFramework("AppKit"),
                .linkedFramework("CoreGraphics"),
                .linkedFramework("IOKit"),
                .linkedFramework("ServiceManagement"),
                .linkedFramework("Carbon")
            ]
        )
    ]
)
