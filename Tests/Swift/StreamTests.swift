import XCTest
@testable import GlanceCore
final class StreamTests: XCTestCase {
    func testCoalescesNDJSONPreservesPartialAndIgnoresHeartbeatOnlyChanges() throws {
        var stream = SnapshotStream()
        let first = "{\"connected\":true,\"updatedAt\":\"1\",\"sessions\":[{\"id\":\"a\"}]}"
        let second = first.replacingOccurrences(of: "\"1\"", with: "\"2\"")
        XCTAssertNil(stream.append(Data(first.prefix(10).utf8)))
        let newest = try XCTUnwrap(stream.append(Data((String(first.dropFirst(10)) + "\n" + second + "\n").utf8)))
        XCTAssertEqual(newest.updatedAt, "2")
        let older = try JSONDecoder().decode(Snapshot.self, from: Data(first.utf8))
        XCTAssertTrue(newest.hasSameContent(as: older))
        XCTAssertNil(stream.append(Data(" \n".utf8)))
        let invalid = try XCTUnwrap(stream.append(Data("not-json\n".utf8)))
        XCTAssertNotNil(invalid.error)
        XCTAssertFalse(invalid.hasSameContent(as: newest))
        XCTAssertTrue(try XCTUnwrap(stream.append(Data(("bad\n" + first + "\n").utf8))).connected)
    }
}
