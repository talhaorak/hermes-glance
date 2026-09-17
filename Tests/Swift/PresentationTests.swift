import XCTest
@testable import GlanceCore
final class PresentationTests: XCTestCase {
    func snapshot(_ status: String, time: String = "1") throws -> Snapshot {
        try JSONDecoder().decode(Snapshot.self, from: Data("{\"connected\":true,\"updatedAt\":\"\(time)\",\"sessions\":[{\"id\":\"a\",\"status\":\"\(status)\"}]}".utf8))
    }
    func testCompactDensityLeavesSevenRowsEvenWithCollapsedWarning() {
        let usable = 680.0 - 29 - GlanceLayout.chromeHeight - 12 - 26
        let rows = Int((usable + GlanceLayout.rowSpacing) / (GlanceLayout.rowHeight + GlanceLayout.rowSpacing))
        XCTAssertEqual(GlanceLayout.rowHeight, 68)
        XCTAssertLessThanOrEqual(GlanceLayout.chromeHeight, 51)
        XCTAssertGreaterThanOrEqual(rows, 7)
    }
    func testRefreshKeepsExpansionAndOnlySignalsObservedCompletionBriefly() throws {
        var state = SessionPresentation()
        state.toggleExpansion("a")
        let now = Date(timeIntervalSince1970: 100)
        state.update(try snapshot("running"), now: now)
        state.update(try snapshot("completed"), now: now)
        XCTAssertTrue(state.expandedIDs.contains("a"))
        XCTAssertEqual(state.completedIDs, ["a"])
        state.update(try snapshot("completed", time: "2"), now: now.addingTimeInterval(5))
        state.expire(now: now.addingTimeInterval(9))
        XCTAssertTrue(state.completedIDs.isEmpty)
        state.update(try snapshot("completed"), now: now.addingTimeInterval(10))
        XCTAssertTrue(state.completedIDs.isEmpty)
        state.toggleExpansion("a")
        XCTAssertTrue(state.expandedIDs.isEmpty)
        var initial = SessionPresentation()
        initial.update(try snapshot("completed"), now: now)
        XCTAssertTrue(initial.completedIDs.isEmpty)
        initial.update(try snapshot("running"), now: now)
        initial.update(try snapshot("idle"), now: now)
        XCTAssertTrue(initial.completedIDs.isEmpty, "Idle is not evidence of completion")
    }
}
