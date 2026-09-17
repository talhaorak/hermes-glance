import AppKit
import SwiftUI
import GlanceCore

final class GlancePanel: NSPanel {
    override var canBecomeKey: Bool { true }
    override var canBecomeMain: Bool { false }
}

final class WindowController: NSObject, ObservableObject, NSWindowDelegate {
    @Published var alwaysOnTop: Bool = UserDefaults.standard.object(forKey: "alwaysOnTop") as? Bool ?? true {
        didSet { panel?.level = alwaysOnTop ? .floating : .normal; UserDefaults.standard.set(alwaysOnTop, forKey: "alwaysOnTop") }
    }
    private(set) var panel: GlancePanel!
    private let frameKey = "GlanceWindowFrame"
    init(store: BridgeStore) {
        super.init()
        let screens = NSScreen.screens.map(\.visibleFrame)
        var frame = WindowGeometry.initialFrame(screens: screens)
        if let saved = UserDefaults.standard.string(forKey: frameKey) {
            let candidate = NSRectFromString(saved)
            if let screen = screens.first(where: { $0.intersects(candidate) }) { frame = WindowGeometry.clamp(candidate, to: screen) }
        }
        panel = GlancePanel(contentRect: frame, styleMask: [.titled, .closable, .resizable, .fullSizeContentView, .nonactivatingPanel], backing: .buffered, defer: false)
        panel.title = "Hermes Glance"
        panel.titleVisibility = .hidden
        panel.titlebarAppearsTransparent = true
        panel.isMovableByWindowBackground = true
        panel.isReleasedWhenClosed = false
        panel.hidesOnDeactivate = false
        panel.becomesKeyOnlyIfNeeded = true
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        panel.level = alwaysOnTop ? .floating : .normal
        panel.minSize = NSSize(width: 360, height: 320)
        panel.maxSize = NSSize(width: 640, height: 1800)
        panel.backgroundColor = NSColor(red: 0.965, green: 0.961, blue: 0.933, alpha: 1)
        panel.standardWindowButton(.zoomButton)?.isHidden = true
        panel.standardWindowButton(.miniaturizeButton)?.isHidden = true
        panel.contentView = NSHostingView(rootView: GlanceView(store: store, window: self))
        panel.delegate = self
        panel.setFrame(frame, display: false)
        NotificationCenter.default.addObserver(self, selector: #selector(screensChanged), name: NSApplication.didChangeScreenParametersNotification, object: nil)
    }
    func show() { panel.orderFrontRegardless() }
    func hide() { panel.orderOut(nil) }
    func toggle() { panel.isVisible ? hide() : show() }
    func move(to screen: NSScreen) {
        let rect = CGRect(x: screen.visibleFrame.maxX - panel.frame.width - 24, y: screen.visibleFrame.maxY - panel.frame.height - 24, width: panel.frame.width, height: panel.frame.height)
        panel.setFrame(WindowGeometry.clamp(rect, to: screen.visibleFrame), display: true, animate: false)
        show(); saveFrame()
    }
    func windowShouldClose(_ sender: NSWindow) -> Bool { hide(); return false }
    func windowDidMove(_ notification: Notification) { saveFrame() }
    func windowDidResize(_ notification: Notification) { saveFrame() }
    private func saveFrame() { UserDefaults.standard.set(NSStringFromRect(panel.frame), forKey: frameKey) }
    @objc private func screensChanged() {
        let screens = NSScreen.screens
        guard let screen = screens.first(where: { $0.visibleFrame.intersects(panel.frame) }) ?? screens.first else { return }
        panel.setFrame(WindowGeometry.clamp(panel.frame, to: screen.visibleFrame), display: true)
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate, NSMenuDelegate {
    let store = BridgeStore()
    var window: WindowController!
    var statusItem: NSStatusItem!
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)
        window = WindowController(store: store)
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        statusItem.button?.image = NSImage(systemSymbolName: "leaf", accessibilityDescription: "Hermes Glance")
        statusItem.button?.toolTip = "Hermes Glance"
        let menu = NSMenu(); menu.delegate = self; statusItem.menu = menu
        window.show(); store.start()
    }
    func menuNeedsUpdate(_ menu: NSMenu) {
        menu.removeAllItems()
        add(window.panel.isVisible ? "Hide Hermes Glance" : "Show Hermes Glance", action: #selector(toggle), to: menu)
        let pin = add("Always on top", action: #selector(togglePin), to: menu)
        pin.state = window.alwaysOnTop ? .on : .off
        let displays = NSMenu()
        for (index, screen) in NSScreen.screens.enumerated() {
            let item = add("\(index + 1) · \(screen.localizedName)", action: #selector(moveDisplay(_:)), to: displays)
            item.tag = index
            item.state = window.panel.screen == screen ? .on : .off
        }
        let displayItem = NSMenuItem(title: "Move to display", action: nil, keyEquivalent: "")
        displayItem.submenu = displays; menu.addItem(displayItem)
        add("Reconnect monitor", action: #selector(reconnect), to: menu)
        menu.addItem(.separator())
        let quit = add("Quit Hermes Glance", action: #selector(quit), to: menu); quit.keyEquivalent = "q"
    }
    @discardableResult private func add(_ title: String, action: Selector, to menu: NSMenu) -> NSMenuItem {
        let item = NSMenuItem(title: title, action: action, keyEquivalent: ""); item.target = self; menu.addItem(item); return item
    }
    @objc private func toggle() { window.toggle() }
    @objc private func togglePin() { window.alwaysOnTop.toggle() }
    @objc private func moveDisplay(_ sender: NSMenuItem) { guard NSScreen.screens.indices.contains(sender.tag) else { return }; window.move(to: NSScreen.screens[sender.tag]) }
    @objc private func reconnect() { store.start() }
    @objc private func quit() { NSApp.terminate(nil) }
    func applicationWillTerminate(_ notification: Notification) { store.stop() }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { false }
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool { window.show(); return true }
}
