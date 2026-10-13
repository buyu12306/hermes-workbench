#!/usr/bin/env bash
# Step 1 (retry): install npm workspace dependencies with CN mirrors for the two
# GitHub-hosted binary downloads this machine cannot reach directly:
#   - electron  -> npmmirror binary mirror (ELECTRON_MIRROR)
#   - get-windows (node-pre-gyp) -> GitHub release asset via gh-proxy accelerator
#     (npm_config_node_get_windows_binary_host_mirror, supported by node-pre-gyp)
set -euo pipefail
REPO="C:/Users/<用户名>/Desktop/hermes-agent-main"
export PATH="/c/Program Files/nodejs:$PATH"
export CI=1
export HERMES_PYTHON="$REPO/.venv/Scripts/python.exe"
export PYTHON="$REPO/.venv/Scripts/python.exe"
export ELECTRON_MIRROR="https://registry.npmmirror.com/-/binary/electron/"
export npm_config_node_get_windows_binary_host_mirror="https://gh-proxy.com/https://github.com/sindresorhus/get-windows/releases/download/"
cd "$REPO"
echo "[workbench] node: $(node --version)  npm: $(npm --version)"
echo "[workbench] ELECTRON_MIRROR=$ELECTRON_MIRROR"
echo "[workbench] get-windows mirror=$npm_config_node_get_windows_binary_host_mirror"
node scripts/build/node-deps.mjs --source "$REPO" --reuse \
  --workspace ui-tui --workspace web --workspace apps/desktop
echo "[workbench] node-deps complete"
