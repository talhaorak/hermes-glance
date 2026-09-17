import XCTest
@testable import GlanceCore
final class GlanceCoreTests: XCTestCase {
    func session(_ id: String, _ status: String, _ date: String = "2026-09-18T00:00:00Z", url: String = "") throws -> GlanceSession {
        let data = try JSONSerialization.data(withJSONObject: ["id":id,"status":status,"updatedAt":date,"openURL":url])
        return try JSONDecoder().decode(GlanceSession.self, from: data)
    }
    func testWaitingPriorityStableTieBreakingAndFilters() throws {
        let sessions = try [session("z", "running"), session("b", "waiting"), session("a", "waiting"), session("x", "completed")]
        XCTAssertEqual(SessionFilter.all.apply(sessions).map(\.id), ["a", "b", "z", "x"])
        XCTAssertEqual(SessionFilter.running.apply(sessions).map(\.id), ["z"])
        XCTAssertEqual(SessionFilter.waiting.apply(sessions).map(\.id), ["a", "b"])
    }
    func testActiveExcludesHistoryAndKeepsWaitingFirst() throws {
        let sessions = try [session("idle", "idle"), session("run", "running"), session("wait", "waiting"), session("done", "completed"), session("lost", "unknown")]
        let active = SessionFilter(rawValue: "Aktif") ?? .all
        XCTAssertEqual(active.apply(sessions).map(\.id), ["wait", "run"])
    }
    func testActivityContractBoundsRecentLinesAndFallsBackHonestly() throws {
        let data = try JSONSerialization.data(withJSONObject: ["id":"a", "activity":"Reading file", "live":true, "activityAt":"now", "lines":(1...15).map(String.init)])
        let value = try JSONDecoder().decode(GlanceSession.self, from: data)
        XCTAssertEqual(value.lines.count, 12)
        XCTAssertEqual(value.lines.first, "4")
        XCTAssertEqual(value.activity, "Reading file")
        XCTAssertEqual(value.live, true)
        XCTAssertEqual(value.activityAt, "now")
        XCTAssertEqual(value.latestActivity, "Reading file")
        XCTAssertEqual(try session("old", "idle").latestActivity, "Henüz etkinlik yok")
        XCTAssertFalse(try session("old", "idle").live)
    }
    func testOnlyHermesDeepLinksAreAccepted() throws {
        XCTAssertNotNil(try session("a", "running", url: "hermes://session/a").validatedURL)
        for url in ["https://example.com", "file:///etc/passwd", "javascript:alert(1)", "hermes:", ""] {
            XCTAssertNil(try session("a", "running", url: url).validatedURL)
        }
    }
    func testGeometryUsesSecondDisplayAndClampsRestoredFrames() {
        let screens = [CGRect(x: 0, y: 0, width: 1440, height: 900), CGRect(x: -1920, y: 50, width: 1920, height: 1080)]
        let frame = WindowGeometry.initialFrame(screens: screens)
        XCTAssertTrue(screens[1].contains(frame))
        XCTAssertEqual(frame.width, 400)
        let clamped = WindowGeometry.clamp(CGRect(x: 8000, y: -5000, width: 9000, height: 9000), to: screens[0])
        XCTAssertTrue(screens[0].contains(clamped))
        XCTAssertEqual(WindowGeometry.initialFrame(screens: []).width, 400)
    }
    func testBridgeResolutionHonorsOverridesThenBundleThenProject() {
        let paths: Set<String> = ["/bundle/bridge/monitor.py", "/project/bridge/monitor.py", "/opt/homebrew/bin/python3"]
        XCTAssertEqual(BridgeConfiguration.bridgePath(environment: ["GLANCE_BRIDGE":"/custom/monitor.py"], resourcePath: "/bundle", executablePath: "/project/.build/debug/HermesGlance", currentDirectory: "/project", exists: paths.contains), "/custom/monitor.py")
        XCTAssertEqual(BridgeConfiguration.bridgePath(environment: [:], resourcePath: "/bundle", executablePath: "/project/.build/debug/HermesGlance", currentDirectory: "/project", exists: paths.contains), "/bundle/bridge/monitor.py")
        XCTAssertEqual(BridgeConfiguration.bridgePath(environment: [:], resourcePath: nil, executablePath: "/project/.build/debug/HermesGlance", currentDirectory: "/", exists: paths.contains), "/project/bridge/monitor.py")
        XCTAssertEqual(BridgeConfiguration.pythonPath(environment: [:], executable: paths.contains), "/opt/homebrew/bin/python3")
    }
    func testMalformedEntryDoesNotEraseOtherRealSessions() throws {
        let json = #"{"connected":true,"sessions":[{"id":"good","status":"future-status","updatedAt":"2026-09-18T01:02:03.456Z","lines":["1","2","3","4","5"]},{"title":"missing-id"},{"id":"other","summary":null}]}"#
        let snapshot = try JSONDecoder().decode(Snapshot.self, from: Data(json.utf8))
        XCTAssertEqual(snapshot.sessions.map(\.id), ["good", "other"])
        XCTAssertEqual(snapshot.sessions.first?.updatedAt, "2026-09-18T01:02:03.456Z")
        XCTAssertEqual(snapshot.sessions.first?.status, .unknown)
        XCTAssertEqual(snapshot.sessions.last?.summary, "")
    }
    func testMinimalSnapshotDecodesWithoutInventingSessions() throws {
        let snapshot = try JSONDecoder().decode(Snapshot.self, from: Data("{\"connected\":true,\"sessions\":[{\"id\":\"real-1\"}]}".utf8))
        XCTAssertTrue(snapshot.connected)
        XCTAssertEqual(snapshot.sessions.count, 1)
        XCTAssertEqual(snapshot.sessions[0].status, .unknown)
        XCTAssertEqual(snapshot.sessions[0].lines, [])
        XCTAssertNil(snapshot.sessions[0].validatedURL)
    }
}
