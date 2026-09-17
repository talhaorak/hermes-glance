#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
swift test
swift build -c release
BIN="$(swift build -c release --show-bin-path)"
APP="$ROOT/dist/Hermes Glance.app"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$BIN/HermesGlance" "$APP/Contents/MacOS/HermesGlance"
# Only package source; bytecode caches can embed the builder's private paths.
python3 -c 'import pathlib, shutil, sys; source, target = map(pathlib.Path, sys.argv[1:]); shutil.rmtree(target, ignore_errors=True); target.mkdir(parents=True); shutil.copy2(source / "monitor.py", target / "monitor.py")' "$ROOT/bridge" "$APP/Contents/Resources/bridge"
/usr/libexec/PlistBuddy -c 'Clear dict' "$APP/Contents/Info.plist" 2>/dev/null || true
/usr/libexec/PlistBuddy -c 'Add :CFBundleIdentifier string app.hermes-glance.widget' "$APP/Contents/Info.plist"
/usr/libexec/PlistBuddy -c 'Add :CFBundleName string Hermes Glance' "$APP/Contents/Info.plist"
/usr/libexec/PlistBuddy -c 'Add :CFBundleDisplayName string Hermes Glance' "$APP/Contents/Info.plist"
/usr/libexec/PlistBuddy -c 'Add :CFBundleExecutable string HermesGlance' "$APP/Contents/Info.plist"
/usr/libexec/PlistBuddy -c 'Add :CFBundlePackageType string APPL' "$APP/Contents/Info.plist"
/usr/libexec/PlistBuddy -c 'Add :CFBundleShortVersionString string 0.1.0' "$APP/Contents/Info.plist"
/usr/libexec/PlistBuddy -c 'Add :CFBundleVersion string 1' "$APP/Contents/Info.plist"
/usr/libexec/PlistBuddy -c 'Add :LSMinimumSystemVersion string 13.0' "$APP/Contents/Info.plist"
/usr/libexec/PlistBuddy -c 'Add :LSUIElement bool true' "$APP/Contents/Info.plist"
/usr/libexec/PlistBuddy -c 'Add :NSHighResolutionCapable bool true' "$APP/Contents/Info.plist"
/usr/bin/codesign --force --sign - "$APP"
/usr/bin/codesign --verify --strict "$APP"
/usr/bin/plutil -lint "$APP/Contents/Info.plist"
printf '\nBuilt %s\n' "$APP"
