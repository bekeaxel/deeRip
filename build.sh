#!/bin/bash

VERSION="$1"
if [ -z "$VERSION" ]; then
  echo "Usage: ./build.sh <version>"
  exit 1
fi

pyinstaller deeRip.spec --noconfirm

cp assets/terminal-launcher dist/deeRip.app/Contents/MacOS/
chmod +x dist/deeRip.app/Contents/MacOS/terminal-launcher

rm -rf dist/dmg-layout
mkdir -p dist/dmg-layout
cp -R dist/deeRip.app dist/dmg-layout/
ln -s /Applications dist/dmg-layout/Applications

create-dmg --volname "deeRip" \
  --window-pos 200 120 \
  --window-size 500 300 \
  --icon-size 100 \
  --icon "deeRip.app" 100 100 \
  --icon "Applications" 400 100 \
  --hide-extension "deeRip.app" \
  --app-drop-link 400 100 \
  "releases/deeRip-v$VERSION.dmg" \
  "dist/dmg-layout/"