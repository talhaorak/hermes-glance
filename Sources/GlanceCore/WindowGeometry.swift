import Foundation
import CoreGraphics
public enum WindowGeometry {
    public static func initialFrame(screens: [CGRect]) -> CGRect {
        let screen = screens.count > 1 ? screens[1] : screens.first ?? CGRect(x: 0, y: 0, width: 1440, height: 900)
        return clamp(CGRect(x: screen.maxX - 424, y: screen.maxY - 704, width: 400, height: 680), to: screen)
    }
    public static func clamp(_ frame: CGRect, to screen: CGRect) -> CGRect {
        let width = min(max(frame.width, 360), screen.width)
        let height = min(max(frame.height, 320), screen.height)
        return CGRect(x: min(max(frame.minX, screen.minX), screen.maxX - width), y: min(max(frame.minY, screen.minY), screen.maxY - height), width: width, height: height)
    }
}
