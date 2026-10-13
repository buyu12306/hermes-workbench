#!/usr/bin/env bash
# Qoder channel — maxed-params wrapper (2026-10-10).
# Pins thinking effort + context window to the FREE Qwen3.8-Flash's ceiling for every run:
#   --reasoning-effort xhigh  («极高» = the flash-family top level per the Qoder app's
#     model-preferences panel; `max`/`high` get silently dropped to `none` on Qwen3.8-Flash
#     — verified 2026-10-10 via run logs)
#   --context-window 1000000  (1M, the max tier)
# The default model comes from ~/.qoder-cn/settings.json `model.name` (Qwen3.8-Flash, free).
# Usage: bash .build/workbench/72-qoder.sh -p "<task>" [extra qoderclicn args]
set -euo pipefail
exec "C:/Users/<用户名>/.qodersec/bin/qoderclicn.exe" --reasoning-effort xhigh --context-window 1000000 "$@"
