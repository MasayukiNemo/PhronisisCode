#!/bin/bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="BSTBB700Customizer"
BUNDLE_ID="com.buffalo.bstbb700.customizer"
BUILD_DIR="$ROOT/.build/debug"
APP_BUNDLE="$ROOT/$APP_NAME.app"

echo "==> swift build"
swift build --configuration debug

echo "==> create .app bundle at $APP_BUNDLE"
rm -rf "$APP_BUNDLE"
mkdir -p "$APP_BUNDLE/Contents/MacOS"
mkdir -p "$APP_BUNDLE/Contents/Resources"

cp "$BUILD_DIR/$APP_NAME" "$APP_BUNDLE/Contents/MacOS/$APP_NAME"
chmod +x "$APP_BUNDLE/Contents/MacOS/$APP_NAME"

# Info.plist
cat > "$APP_BUNDLE/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleIdentifier</key><string>$BUNDLE_ID</string>
    <key>CFBundleName</key><string>$APP_NAME</string>
    <key>CFBundleExecutable</key><string>$APP_NAME</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>CFBundleVersion</key><string>0.1.0</string>
    <key>CFBundleShortVersionString</key><string>0.1.0</string>
    <key>LSMinimumSystemVersion</key><string>13.0</string>
    <key>LSUIElement</key><true/>
    <key>NSHighResolutionCapable</key><true/>
    <key>NSHumanReadableCopyright</key><string>BUFFALO BSTBB700 Customizer MVP</string>
</dict>
</plist>
EOF

# ad-hoc sign
echo "==> codesign -s - (ad-hoc)"
codesign --force --deep --sign - "$APP_BUNDLE" 2>&1 || echo "codesign warning (ok for ad-hoc)"

# verify
codesign -dv "$APP_BUNDLE" 2>&1 | head -n 20 || true
echo "==> done: $APP_BUNDLE"

if [[ "$1" == "--run" ]]; then
    echo "==> open $APP_BUNDLE"
    open "$APP_BUNDLE"
fi
