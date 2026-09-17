import Foundation
import Combine
import GlanceCore

final class BridgeStore: ObservableObject {
    @Published private(set) var snapshot = Snapshot()
    @Published private(set) var presentation = SessionPresentation()
    private var process: Process?
    private var output: Pipe?
    private var watchdog: Timer?
    private var completionTimer: Timer?
    private var pending: Snapshot?
    private var flush: DispatchWorkItem?
    private var lastReceived = Date()
    private var generation = UUID()
    private var stopped = false
    private let readQueue = DispatchQueue(label: "app.hermes-glance.bridge")

    func toggleExpansion(_ id: String) { presentation.toggleExpansion(id) }
    private func publish(_ value: Snapshot) {
        var next = presentation
        next.update(value)
        if next != presentation { presentation = next }
        if !snapshot.hasSameContent(as: value) { snapshot = value }
        if !presentation.completedIDs.isEmpty && completionTimer == nil {
            completionTimer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak self] _ in
                guard let self else { return }
                var next = self.presentation
                next.expire()
                if next != self.presentation { self.presentation = next }
                if next.completedIDs.isEmpty { self.completionTimer?.invalidate(); self.completionTimer = nil }
            }
        }
    }
    /// A bounded 120ms publication window coalesces bursts across pipe reads too.
    private func receive(_ value: Snapshot, token: UUID) {
        guard generation == token, !stopped else { return }
        lastReceived = Date()
        pending = value
        guard flush == nil else { return }
        let work = DispatchWorkItem { [weak self] in
            guard let self, self.generation == token, !self.stopped else { return }
            self.flush = nil
            if let value = self.pending { self.pending = nil; self.publish(value) }
        }
        flush = work
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.12, execute: work)
    }
    func start() {
        stop()
        stopped = false
        generation = UUID()
        let token = generation
        let env = ProcessInfo.processInfo.environment
        let fm = FileManager.default
        guard let bridge = BridgeConfiguration.bridgePath(environment: env, resourcePath: Bundle.main.resourcePath, executablePath: Bundle.main.executablePath ?? CommandLine.arguments[0], currentDirectory: fm.currentDirectoryPath, exists: fm.fileExists(atPath:)) else {
            publish(Snapshot(error: "Gözlemci bulunamadı. GLANCE_BRIDGE yolunu ayarlayın veya uygulamayı yeniden derleyin."))
            return
        }
        guard let python = BridgeConfiguration.pythonPath(environment: env, executable: fm.isExecutableFile(atPath:)) else {
            publish(Snapshot(error: "Python 3 bulunamadı. GLANCE_PYTHON yolunu ayarlayın."))
            return
        }
        let task = Process(), pipe = Pipe()
        task.executableURL = URL(fileURLWithPath: python)
        task.arguments = ["-u", bridge]
        task.environment = env.merging(["PYTHONUNBUFFERED":"1"]) { _, new in new }
        task.standardOutput = pipe
        task.standardError = FileHandle.standardError
        task.terminationHandler = { [weak self] ended in
            DispatchQueue.main.async {
                guard let self, self.generation == token, !self.stopped else { return }
                self.flush?.cancel(); self.flush = nil; self.pending = nil
                self.publish(Snapshot(error: "Gözlemci durdu (\(ended.terminationStatus)). Yeniden bağlanılıyor…"))
                self.watchdog?.invalidate()
                DispatchQueue.main.asyncAfter(deadline: .now() + 5) { [weak self] in
                    guard let self, self.generation == token, !self.stopped else { return }
                    self.start()
                }
            }
        }
        do {
            try task.run()
            process = task; output = pipe; lastReceived = Date()
            publish(Snapshot(error: "Yerel oturumlara bağlanılıyor…"))
            readQueue.async { [weak self] in
                var stream = SnapshotStream()
                while true {
                    let bytes = pipe.fileHandleForReading.availableData
                    if bytes.isEmpty { break }
                    if let value = stream.append(bytes) {
                        DispatchQueue.main.async { [weak self] in self?.receive(value, token: token) }
                    }
                }
            }
            watchdog = Timer.scheduledTimer(withTimeInterval: 10, repeats: true) { [weak self] _ in
                guard let self, Date().timeIntervalSince(self.lastReceived) > 30 else { return }
                self.start()
            }
        } catch {
            publish(Snapshot(error: "Gözlemci başlatılamadı: \(error.localizedDescription)"))
        }
    }
    func stop() {
        stopped = true; generation = UUID()
        flush?.cancel(); flush = nil; pending = nil
        completionTimer?.invalidate(); completionTimer = nil
        watchdog?.invalidate(); watchdog = nil
        process?.terminationHandler = nil
        if process?.isRunning == true { process?.terminate() }
        process = nil; output = nil
    }
    deinit { stop() }
}
