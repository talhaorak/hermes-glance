import Foundation

public enum SessionStatus: String, Codable { case running, waiting, idle, completed, unknown }
public struct GlanceSession: Decodable, Identifiable, Equatable {
    public let id: String
    public let title: String
    public let profile: String
    public let status: SessionStatus
    public let summary: String
    public let lines: [String]
    public let updatedAt: String?
    public let openURL: String?
    public let waitingReason: String?
    public let activity: String?
    public let live: Bool
    public let activityAt: String?
    public var latestActivity: String {
        if status == .waiting, let reason = waitingReason, !reason.isEmpty { return reason }
        return [activity, summary, lines.last].compactMap { $0 }.first { !$0.isEmpty } ?? "Henüz etkinlik yok"
    }
    enum CodingKeys: String, CodingKey { case id, title, profile, status, summary, lines, updatedAt, openURL, waitingReason, activity, live, activityAt }
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decode(String.self, forKey: .id)
        title = (try? c.decode(String.self, forKey: .title)) ?? "Untitled session"
        profile = (try? c.decode(String.self, forKey: .profile)) ?? "default"
        status = SessionStatus(rawValue: (try? c.decode(String.self, forKey: .status)) ?? "") ?? .unknown
        summary = (try? c.decode(String.self, forKey: .summary)) ?? ""
        lines = Array(((try? c.decode([String].self, forKey: .lines)) ?? []).suffix(12))
        updatedAt = try? c.decode(String.self, forKey: .updatedAt)
        openURL = try? c.decode(String.self, forKey: .openURL)
        waitingReason = try? c.decode(String.self, forKey: .waitingReason)
        activity = try? c.decode(String.self, forKey: .activity)
        live = (try? c.decode(Bool.self, forKey: .live)) ?? false
        activityAt = try? c.decode(String.self, forKey: .activityAt)
    }
    public var validatedURL: URL? {
        guard let raw = openURL, let url = URL(string: raw), url.scheme?.lowercased() == "hermes",
              let host = url.host, !host.isEmpty, url.user == nil, url.password == nil else { return nil }
        return url
    }
}
public struct Snapshot: Decodable {
    public let connected: Bool
    public let updatedAt: String?
    public let error: String?
    public let sessions: [GlanceSession]
    enum CodingKeys: String, CodingKey { case connected, updatedAt, error, sessions }
    public init(connected: Bool = false, updatedAt: String? = nil, error: String? = nil, sessions: [GlanceSession] = []) {
        self.connected = connected; self.updatedAt = updatedAt; self.error = error; self.sessions = sessions
    }
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        connected = (try? c.decode(Bool.self, forKey: .connected)) ?? false
        updatedAt = try? c.decode(String.self, forKey: .updatedAt)
        error = try? c.decode(String.self, forKey: .error)
        var decoded: [GlanceSession] = []
        if var items = try? c.nestedUnkeyedContainer(forKey: .sessions) {
            while !items.isAtEnd {
                let item = try items.superDecoder()
                if let session = try? GlanceSession(from: item), !session.id.isEmpty { decoded.append(session) }
            }
        }
        sessions = decoded
    }
}
