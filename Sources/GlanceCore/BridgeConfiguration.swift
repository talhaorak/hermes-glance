import Foundation
public enum BridgeConfiguration {
    public static func bridgePath(environment: [String:String], resourcePath: String?, executablePath: String, currentDirectory: String, exists: (String) -> Bool) -> String? {
        if let override = environment["GLANCE_BRIDGE"], !override.isEmpty { return (override as NSString).expandingTildeInPath }
        var candidates = resourcePath.map { [$0 + "/bridge/monitor.py"] } ?? []
        var ancestor = URL(fileURLWithPath: executablePath).deletingLastPathComponent()
        for _ in 0..<7 {
            candidates.append(ancestor.appendingPathComponent("bridge/monitor.py").path)
            ancestor.deleteLastPathComponent()
        }
        candidates.append(URL(fileURLWithPath: currentDirectory).appendingPathComponent("bridge/monitor.py").path)
        return candidates.first(where: exists)
    }
    public static func pythonPath(environment: [String:String], executable: (String) -> Bool) -> String? {
        if let override = environment["GLANCE_PYTHON"], !override.isEmpty {
            let expanded = (override as NSString).expandingTildeInPath
            if expanded.contains("/") { return expanded }
            return (environment["PATH"] ?? "").split(separator: ":").map { "\($0)/\(expanded)" }.first(where: executable)
        }
        let candidates = (environment["PATH"] ?? "").split(separator: ":").map { "\($0)/python3" } + ["/opt/homebrew/bin/python3", "/usr/local/bin/python3", "/usr/bin/python3"]
        return candidates.first(where: executable)
    }
}
