#!/usr/bin/env bash
# Step 3: pack the unpacked Windows app (electron-builder --dir) exactly as
# `hermes desktop` would, with the CN mirror for electron-builder's own
# GitHub-hosted helper binaries.
set -euo pipefail
REPO="C:/Users/<用户名>/Desktop/hermes-agent-main"
export PATH="/c/Program Files/nodejs:$PATH"
export CI=1
export HERMES_PYTHON="$REPO/.venv/Scripts/python.exe"
export ELECTRON_MIRROR="https://registry.npmmirror.com/-/binary/electron/"
export ELECTRON_BUILDER_BINARIES_MIRROR="https://registry.npmmirror.com/-/binary/electron-builder-binaries/"
cd "$REPO/apps/desktop"
npm run builder -- --dir --publish never
echo "[workbench] pack complete"
