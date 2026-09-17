// swift-tools-version: 5.9
import PackageDescription
let package = Package(name: "HermesGlance", platforms: [.macOS(.v13)], products: [.executable(name: "HermesGlance", targets: ["HermesGlance"])], targets: [.target(name: "GlanceCore"), .executableTarget(name: "HermesGlance", dependencies: ["GlanceCore"]), .testTarget(name: "GlanceCoreTests", dependencies: ["GlanceCore"], path: "Tests/Swift")], swiftLanguageVersions: [.v5])
