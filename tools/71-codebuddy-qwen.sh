#!/usr/bin/env bash
# [DEPRECATED 2026-10-12] 千问 key 已停用——不要再使用本脚本；原生路线见 71-codebuddy.sh（腾讯账号+限免模型）。
# Run WorkBuddy's CodeBuddy headless CLI on the user's 千问 (qwen) key.
# Usage: bash .build/workbench/71-codebuddy.sh -p "prompt" [--output-format json] [--permission-mode dontAsk] ...
# Verified working 2026-10-09 (replied 「在线」). Env-route = no GUI login needed;
# billing = the user's 千问 key (same token the bridges use).
# Token source of truth: ~/.claude/settings.json env.ANTHROPIC_AUTH_TOKEN (never duplicated here).
set -euo pipefail
TOK=$(python -c 'import json;print(json.load(open("C:/Users/<用户名>/.claude/settings.json",encoding="utf-8"))["env"]["ANTHROPIC_AUTH_TOKEN"])')
export CODEBUDDY_API_KEY="$TOK"
export CODEBUDDY_AUTH_TOKEN="$TOK"
export CODEBUDDY_BASE_URL="https://maas.qianwenaiapi.com/compatible-mode/v1"
export CODEBUDDY_MODEL="${CODEBUDDY_MODEL:-qwen3.8-flash}"
export CODEBUDDY_SKIP_GIT_BASH_CHECK=1
NODE="C:/Users/<用户名>/.workbuddy/binaries/node/versions/22.22.2-6/node.exe"
CLI="C:/Users/<用户名>/AppData/Local/Programs/WorkBuddy/resources/app.asar.unpacked/cli/dist/codebuddy-headless.js"
exec "$NODE" "$CLI" "$@"
