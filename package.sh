#!/usr/bin/env bash
# Zip the release fonts for a GitHub release. Run after ./build.sh.
set -euo pipefail
cd "$(dirname "$0")"
VER="${1:-0.1.0}"
rm -rf "release/IseGrotesk-$VER"; mkdir -p "release/IseGrotesk-$VER"
cp -R release/ttf release/otf release/woff2 "release/IseGrotesk-$VER/"
cp OFL.txt README.md "release/IseGrotesk-$VER/"
(cd release && zip -rq "IseGrotesk-$VER.zip" "IseGrotesk-$VER" -x "*.DS_Store")
echo "Created release/IseGrotesk-$VER.zip"
