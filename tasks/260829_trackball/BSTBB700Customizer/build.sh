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

# sign with stable local cert if available, otherwise ad-hoc (ad-hoc requires re-grant after each build)
# Ensure custom keychain is in search list
security list-keychains -d user -s /tmp/bstbb700.keychain ~/Library/Keychains/login.keychain-db 2>&1 | head -n 5 || true
if security find-identity -v -p codesigning /tmp/bstbb700.keychain 2>&1 | grep -q "BSTBB700 Local2"; then
    echo "==> codesign with BSTBB700 Local2 (stable, no re-grant needed)"
    security unlock-keychain -p bstbb700 /tmp/bstbb700.keychain 2>&1 | head -n 5 || true
    codesign --force --deep --sign "BSTBB700 Local2" --keychain /tmp/bstbb700.keychain "$APP_BUNDLE" 2>&1 || {
        echo "codesign Local2 failed, fallback to ad-hoc"
        codesign --force --deep --sign - "$APP_BUNDLE" 2>&1 || echo "codesign warning (ok for ad-hoc)"
    }
else
    echo "==> codesign -s - (ad-hoc, requires re-grant after each rebuild)"
    codesign --force --deep --sign - "$APP_BUNDLE" 2>&1 || echo "codesign warning (ok for ad-hoc)"
fi

# verify
codesign -dv "$APP_BUNDLE" 2>&1 | head -n 20 || true
echo "==> done: $APP_BUNDLE"

if [[ "$1" == "--run" ]]; then
    echo "==> open $APP_BUNDLE"
    open "$APP_BUNDLE"
fi
