import AppKit

@MainActor
func mainActorBootstrap() {
    let delegate = AppDelegate()
    let app = NSApplication.shared
    app.delegate = delegate
    _ = NSApplicationMain(CommandLine.argc, CommandLine.unsafeArgv)
}

// NSApplicationMainはメインスレッドで呼ぶ必要がある
if Thread.isMainThread {
    MainActor.assumeIsolated {
        mainActorBootstrap()
    }
} else {
    DispatchQueue.main.sync {
        MainActor.assumeIsolated {
            mainActorBootstrap()
        }
    }
}
