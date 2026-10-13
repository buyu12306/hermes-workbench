#!/usr/bin/env bash
# tools/dispatch-claude.sh —— 《执行架构》通道 A 封装：把交接单派给 Claude Code CLI
#
# 用法：bash tools/dispatch-claude.sh <交接单.txt> [工作目录] [最大回合数]
#   交接单.txt  任务简报（背景 / 任务与要求 / 验收标准 / 禁止事项，四要素见 docs/orchestration.md）
#   工作目录    默认当前目录（Claude Code 在该目录内工作；产物也落在这里）
#   最大回合数  默认 40
#
# 行为：以 print 模式运行 claude，输出写入 <工作目录>/dispatch-claude.log，
#       日志末尾追加 EXIT=<退出码>。
# 注意：① 长任务请把本脚本作为“后台任务”启动（Hermes：background=true；
#         原生终端：nohup bash this.sh … &），否则会被调用方前台超时上限打断；
#       ② 前置：本机已安装并登录 Claude Code CLI（见 docs/reproduction.md 第 2 节）。
set -u
if [ $# -lt 1 ]; then
  echo "用法: bash tools/dispatch-claude.sh <交接单.txt> [工作目录] [最大回合数]" >&2
  exit 2
fi
BRIEF="$1"
WORKDIR="${2:-.}"
MAXTURNS="${3:-40}"
if [ ! -f "$BRIEF" ]; then
  echo "错误：找不到交接单 $BRIEF" >&2
  exit 2
fi
mkdir -p "$WORKDIR"
cd "$WORKDIR" || exit 2
LOG="$WORKDIR/dispatch-claude.log"
claude -p "$(cat "$BRIEF")" \
  --max-turns "$MAXTURNS" \
  --allowedTools "Read,Write,Edit,Bash" \
  --permission-mode auto \
  --verbose > "$LOG" 2>&1
echo "EXIT=$?" >> "$LOG"
echo "完成：日志见 $LOG"
