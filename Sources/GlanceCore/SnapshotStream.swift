import Foundation

public extension Snapshot {
    /// Transport heartbeat timestamps are not UI changes.
    func hasSameContent(as other: Snapshot) -> Bool {
        connected == other.connected && error == other.error && sessions == other.sessions
    }
}

/// Incremental NDJSON parser; publish only the newest complete record in each read.
public struct SnapshotStream {
    private var buffer = Data()
    public init() {}
    public mutating func append(_ bytes: Data) -> Snapshot? {
        buffer.append(bytes)
        var latest: Snapshot?
        while let end = buffer.firstIndex(of: 10) {
            let line = Data(buffer[..<end]); buffer.removeSubrange(...end)
            if line.allSatisfy({ $0 == 32 || $0 == 13 || $0 == 9 }) { continue }
            latest = (try? JSONDecoder().decode(Snapshot.self, from: line)) ?? Snapshot(error: "Geçersiz gözlemci verisi; sonraki güncelleme bekleniyor.")
        }
        if buffer.count > 8_000_000 {
            buffer.removeAll()
            latest = Snapshot(error: "Gözlemci verisi boyut sınırını aştı.")
        }
        return latest
    }
}
