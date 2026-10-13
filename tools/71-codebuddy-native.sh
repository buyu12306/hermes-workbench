#!/usr/bin/env bash
# WorkBuddy CodeBuddy CLI — NATIVE route (default since 2026-10-10).
# Uses the standalone CodeBuddy Code install (C:\Users\<用户名>\AppData\Local\codebuddy\bin\codebuddy.exe)
# on the user's own logged-in Tencent account. Defaults come from ~/.codebuddy/settings.json:
#   model=hy4-preview-f, effort=max, autoCompactWindow=960000, alwaysThinkingEnabled=true.
# Legacy qianwen-gateway route: bash .build/workbench/71-codebuddy-qwen.sh ...
# Usage: bash .build/workbench/71-codebuddy.sh -p "<prompt>" [--permission-mode acceptEdits] ...
set -euo pipefail
export CODEBUDDY_SKIP_GIT_BASH_CHECK=1
exec "C:/Users/<用户名>/AppData/Local/codebuddy/bin/codebuddy.exe" "$@"
