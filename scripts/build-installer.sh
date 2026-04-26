#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

APP_PATH="dist/PhotomatorFlagSync.app"
DMG_PATH="dist/PhotomatorFlagSync-installer.dmg"
ZIP_PATH="dist/PhotomatorFlagSync-installer.zip"

if [[ ! -d "$APP_PATH" ]]; then
  echo "App bundle not found at $APP_PATH"
  echo "Run scripts/build-app.sh first."
  exit 1
fi

rm -f "$DMG_PATH" "$ZIP_PATH"

if command -v create-dmg >/dev/null 2>&1; then
  create-dmg \
    --volname "PhotomatorFlagSync Installer" \
    --window-pos 200 120 \
    --window-size 800 400 \
    --icon-size 100 \
    --icon "PhotomatorFlagSync.app" 200 190 \
    --hide-extension "PhotomatorFlagSync.app" \
    --app-drop-link 600 185 \
    "$DMG_PATH" \
    "$APP_PATH"
  echo "Built DMG installer: $DMG_PATH"
else
  echo "create-dmg not found; building ZIP installer fallback."
  ditto -c -k --sequesterRsrc --keepParent "$APP_PATH" "$ZIP_PATH"
  echo "Built ZIP installer: $ZIP_PATH"
  echo "Tip: brew install create-dmg for DMG output."
fi
