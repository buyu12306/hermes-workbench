#!/bin/bash
# push-workbench2.sh — final push path: userinfo URL + clean gh helper chain + MyClash proxy.
cd "/c/Users/<用户名>/Desktop/工作区/hermes-workbench-repo" || exit 1
LOG=/c/Users/<用户名>/AppData/Local/hermes/cache/scratch/push2.log
exec > "$LOG" 2>&1
echo "=== $(date '+%F %T') push2 start ==="
export GIT_CONFIG_COUNT=2 GIT_CONFIG_KEY_0=credential.helper GIT_CONFIG_VALUE_0= GIT_CONFIG_KEY_1=credential.helper GIT_CONFIG_VALUE_1="!'C:/Users/<用户名>/AppData/Local/hermes/tools/gh/bin/gh.exe' auth git-credential"
export GIT_TERMINAL_PROMPT=0
export HTTPS_PROXY=http://127.0.0.1:7877 HTTP_PROXY=http://127.0.0.1:7877 NO_PROXY='127.0.0.1,localhost,::1'
timeout -s KILL 300 git push -u origin main --verbose
echo "push rc=$?"
echo "--- verify ls-remote ---"
GIT_TERMINAL_PROMPT=0 timeout -s KILL 60 git ls-remote origin 2>&1 | head -6
echo "verify rc=$?"
echo "=== done $(date '+%F %T') ==="
