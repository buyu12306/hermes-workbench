#!/usr/bin/env bash
# Step 2: build the desktop app (renderer + electron main + build stamp +
# native deps staging) exactly as `hermes desktop` would, using system npm.
set -euo pipefail
REPO="C:/Users/<用户名>/Desktop/hermes-agent-main"
export PATH="/c/Program Files/nodejs:$PATH"
export CI=1
export HERMES_PYTHON="$REPO/.venv/Scripts/python.exe"
export PYTHON="$REPO/.venv/Scripts/python.exe"
cd "$REPO/apps/desktop"
npm run build
echo "[workbench] desktop build complete"
