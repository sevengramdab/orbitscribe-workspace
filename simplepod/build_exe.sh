#!/bin/bash
set -e

cd "$(dirname "$0")"
pyinstaller simplepod.spec --clean --noconfirm

mkdir -p release
cp -r dist/SimplePod release/

echo ""
echo "Build successful! Output copied to release/SimplePod"
