import Foundation

/// View-only state: never writes to Hermes and never infers completion from silence.
public struct SessionPresentation: Equatable {
    public private(set) var expandedIDs = Set<String>()
    private var previous: [String: SessionStatus] = [:]
    private var completionDeadlines: [String: Date] = [:]
    public var completedIDs: Set<String> { Set(completionDeadlines.keys) }
    public init() {}
    public mutating func toggleExpansion(_ id: String) {
        if !expandedIDs.insert(id).inserted { expandedIDs.remove(id) }
    }
    public mutating func update(_ snapshot: Snapshot, now: Date = Date()) {
        if snapshot.connected {
            for session in snapshot.sessions {
                if session.status == .completed && previous[session.id] == .running {
                    completionDeadlines[session.id] = now.addingTimeInterval(8)
                } else if session.status != .completed { completionDeadlines.removeValue(forKey: session.id) }
            }
            previous = Dictionary(snapshot.sessions.map { ($0.id, $0.status) }, uniquingKeysWith: { first, _ in first })
        } else {
            previous.removeAll()
            completionDeadlines.removeAll()
        }
        expire(now: now)
    }
    public mutating func expire(now: Date = Date()) {
        completionDeadlines = completionDeadlines.filter { $0.value > now }
    }
}
