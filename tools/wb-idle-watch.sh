#!/bin/bash
# wb-idle-watch.sh — sample CPU/GPU/animation state every ~30s for ~12 min (background diagnostic)
cd "C:/Users/<用户名>/Desktop/hermes-agent-main/.build/workbench" || exit 1
LOG="wb-idle-watch.log"
echo "=== start $(date '+%H:%M:%S') ===" >> "$LOG"
for i in $(seq 1 24); do
  TS=$(date '+%H:%M:%S')
  CPU=$(powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:/Users/<用户名>/Desktop/hermes-agent-main/.build/workbench/wb-cpu-sample.ps1" 2>/dev/null | tr -d '\r')
  ST=$(HERMES_DESKTOP_CDP_PORT=9333 node "C:/Users/<用户名>/Desktop/hermes-agent-main/.build/workbench/cdp-eval-main.mjs" "JSON.stringify({h:(location.hash||'').slice(0,24),idle:document.documentElement.hasAttribute('data-wb-idle'),p:document.documentElement.getAttribute('data-renderer-animations-paused'),an:document.getAnimations().filter(function(a){return a.playState==='running'}).length})" 2>&1 | tail -1 | tr -d '\r')
  echo "[$TS] $CPU || $ST" >> "$LOG"
  if [ $((i % 4)) -eq 1 ]; then
    GPU=$(powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:/Users/<用户名>/Desktop/hermes-agent-main/.build/workbench/wb-gpu-sample.ps1" 2>/dev/null | tr -d '\r' | tr '\n' ' ')
    echo "      GPU: $GPU" >> "$LOG"
  fi
  sleep 24
done
echo "=== end $(date '+%H:%M:%S') ===" >> "$LOG"
