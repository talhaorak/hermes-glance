import Foundation
public enum SessionFilter: String, CaseIterable {
    case active = "Aktif", all = "Tümü", waiting = "Bekleyen", running = "Çalışan"
    public static var allCases: [SessionFilter] { [.active, .all, .waiting] }
    public func apply(_ sessions: [GlanceSession]) -> [GlanceSession] {
        var seen = Set<String>()
        return sessions.filter {
            seen.insert($0.id).inserted && (self == .all ||
                (self == .active && ($0.status == .running || $0.status == .waiting)) ||
                (self == .waiting && $0.status == .waiting) || (self == .running && $0.status == .running))
        }.sorted {
            let ranks: [SessionStatus:Int] = [.waiting:0,.running:1,.idle:2,.unknown:3,.completed:4]
            let a = ranks[$0.status]!, b = ranks[$1.status]!
            if a != b { return a < b }
            return $0.id < $1.id
        }
    }
}
