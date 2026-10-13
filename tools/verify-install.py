#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/verify-install.py —— Hermes 工作台一键安装自检脚本

用途：
  复刻者装机后运行本脚本，一次性核对六项关键组件是否就绪：
    1. 网关      ：GET http://127.0.0.1:8787/v1/models（Authorization: Bearer codebuddy-local）返回 200
    2. 防睡眠守护 ：90-keepawake.cmd status 输出包含 RUNNING
    3. 额度守卫   ：73-wb-quota.py status 退出码为 0 且有输出
    4. 看板库     ：%LOCALAPPDATA%\\hermes\\kanban.db 存在且含 tasks / task_comments / task_events 三表
    5. 插件组件   ：workbench-graph 插件 API 文件存在，desktop-plugins 下三目录齐全
    6. 配置检查   ：config.yaml 存在且不含 <YOUR_API_KEY> 占位符

  每项检查输出 PASS / FAIL / SKIP 三态（缺组件输出 SKIP 并说明原因），
  末尾输出汇总；退出码：无 FAIL 为 0，存在 FAIL 为 1。

用法示例：
  python tools/verify-install.py
  python tools/verify-install.py --hermes-root D:\\hermes-agent-main
  set HERMES_ROOT=D:\\hermes-agent-main
  python tools/verify-install.py

路径解析优先级：命令行参数 --hermes-root > 环境变量 HERMES_ROOT >
默认 %USERPROFILE%\\Desktop\\hermes-agent-main。

依赖：仅 Python 标准库（urllib / subprocess / sqlite3 / pathlib / argparse），兼容 Python 3.10+。
"""

import argparse
import os
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# ---- 常量 ----
GATEWAY_URL = "http://127.0.0.1:8787/v1/models"
GATEWAY_TOKEN = "codebuddy-local"
GATEWAY_TIMEOUT = 5          # 网关检查超时（秒）
SUBPROCESS_TIMEOUT = 10     # 子进程默认超时（秒）
QUOTA_TIMEOUT = 120         # 额度守卫要探测三个模型（实测约 62 秒），单独放宽
REQUIRED_KANBAN_TABLES = ("tasks", "task_comments", "task_events")
REQUIRED_PLUGIN_DIRS = ("workbench-graph", "workbench-overview", "workbench-field")
API_KEY_PLACEHOLDER = "<YOUR_API_KEY>"


def run_subprocess(cmd, timeout=SUBPROCESS_TIMEOUT):
    """执行子进程：默认 10 秒超时（可按需覆盖），UTF-8 解码，异常字符以 replace 替换。"""
    return subprocess.run(
        cmd,
        capture_output=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
    )


def resolve_hermes_root(args):
    """路径解析优先级：--hermes-root 参数 > HERMES_ROOT 环境变量 > 默认桌面路径。"""
    if args.hermes_root:
        return Path(args.hermes_root)
    env_root = os.environ.get("HERMES_ROOT")
    if env_root:
        return Path(env_root)
    user_profile = os.environ.get("USERPROFILE")
    if user_profile:
        return Path(user_profile) / "Desktop" / "hermes-agent-main"
    return Path.home() / "Desktop" / "hermes-agent-main"


def resolve_localappdata():
    """返回 %LOCALAPPDATA%（非 Windows 环境则回退到 AppData\\Local）。"""
    env_path = os.environ.get("LOCALAPPDATA")
    if env_path:
        return Path(env_path)
    return Path.home() / "AppData" / "Local"


def check_gateway():
    """1. 网关：GET /v1/models 期望 HTTP 200。"""
    req = urllib.request.Request(
        GATEWAY_URL,
        headers={"Authorization": "Bearer " + GATEWAY_TOKEN},
    )
    # 绕过系统代理，直连本机网关
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=GATEWAY_TIMEOUT) as resp:
            code = resp.getcode()
    except urllib.error.HTTPError as exc:
        code = exc.code
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        return "FAIL", f"无法访问网关（{exc}）。请先启动网关：startup/CodeBuddy_Gateway.vbs"
    except Exception as exc:  # 兜底，避免自检脚本自身崩溃
        return "FAIL", f"网关检查出现异常（{exc}）。请先启动网关：startup/CodeBuddy_Gateway.vbs"
    if code == 200:
        return "PASS", "网关响应正常（HTTP 200）"
    return "FAIL", f"网关返回 HTTP {code}（期望 200）。请先启动网关：startup/CodeBuddy_Gateway.vbs"


def check_keepawake(hermes_root):
    """2. 防睡眠守护：90-keepawake.cmd status 输出包含 RUNNING。"""
    cmd_file = hermes_root / ".build" / "workbench" / "90-keepawake.cmd"
    if not cmd_file.is_file():
        return "SKIP", "未找到 90-keepawake.cmd，跳过防睡眠守护检查"
    try:
        proc = run_subprocess(["cmd", "/c", str(cmd_file), "status"])
    except subprocess.TimeoutExpired:
        return "FAIL", "执行 90-keepawake.cmd status 超时（10 秒）"
    except OSError as exc:
        return "FAIL", f"执行 90-keepawake.cmd 失败：{exc}"
    output = (proc.stdout or "") + (proc.stderr or "")
    if "RUNNING" in output:
        return "PASS", "防睡眠守护正在运行（RUNNING）"
    return "FAIL", f"防睡眠守护未运行（输出中未找到 RUNNING）。输出：{output.strip() or '（无输出）'}"


def check_quota(hermes_root):
    """3. 额度守卫：73-wb-quota.py status 退出码 0 且有输出。"""
    quota_file = hermes_root / ".build" / "workbench" / "73-wb-quota.py"
    if not quota_file.is_file():
        return "SKIP", "未找到 73-wb-quota.py，跳过额度守卫检查"
    try:
        proc = run_subprocess([sys.executable, str(quota_file), "status"], timeout=QUOTA_TIMEOUT)
    except subprocess.TimeoutExpired:
        return "FAIL", "执行 73-wb-quota.py status 超时（120 秒）"
    except OSError as exc:
        return "FAIL", f"执行 73-wb-quota.py 失败：{exc}"
    output = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode == 0 and output.strip():
        return "PASS", "额度守卫运行正常（退出码 0）"
    return "FAIL", f"额度守卫异常：退出码 {proc.returncode}，输出：{output.strip() or '（无输出）'}"


def check_kanban(localappdata):
    """4. 看板库：kanban.db 存在且含三张数据表（只读方式打开）。"""
    db_file = localappdata / "hermes" / "kanban.db"
    if not db_file.is_file():
        return "SKIP", "未找到看板库 kanban.db。首次打开桌面端看板会自动建库"
    db_uri = "file:{}?mode=ro".format(urllib.parse.quote(db_file.as_posix(), safe="/:"))
    try:
        conn = sqlite3.connect(db_uri, uri=True)
        try:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        finally:
            conn.close()
    except sqlite3.Error as exc:
        return "FAIL", f"打开看板库失败：{exc}"
    tables = {row[0] for row in rows}
    missing = [name for name in REQUIRED_KANBAN_TABLES if name not in tables]
    if not missing:
        return "PASS", "看板库完整（tasks / task_comments / task_events）"
    return "FAIL", "看板库缺少数据表：" + "、".join(missing)


def check_plugins(localappdata):
    """5. 插件：plugin_api.py 存在且 desktop-plugins 三目录齐全。"""
    base = localappdata / "hermes"
    plugin_api = base / "plugins" / "workbench-graph" / "dashboard" / "plugin_api.py"
    desktop_plugins = base / "desktop-plugins"
    missing_dirs = [
        name for name in REQUIRED_PLUGIN_DIRS if not (desktop_plugins / name).is_dir()
    ]
    if not plugin_api.is_file() or missing_dirs:
        details = []
        if not plugin_api.is_file():
            details.append("缺少 plugins\\workbench-graph\\dashboard\\plugin_api.py")
        if missing_dirs:
            details.append("desktop-plugins 缺少目录：" + "、".join(missing_dirs))
        return "SKIP", "未检测到完整插件组件（" + "；".join(details) + "）"
    return "PASS", "插件组件齐全（plugin_api.py 与三个插件目录）"


def check_config(localappdata):
    """6. 配置：config.yaml 存在且不含密钥占位符。"""
    config_file = localappdata / "hermes" / "config.yaml"
    if not config_file.is_file():
        return "SKIP", "未找到配置文件 config.yaml"
    try:
        content = config_file.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return "FAIL", f"读取 config.yaml 失败：{exc}"
    if API_KEY_PLACEHOLDER in content:
        return "FAIL", "还有密钥占位符未替换（<YOUR_API_KEY>）"
    return "PASS", "配置文件已就绪，无密钥占位符"


def main():
    parser = argparse.ArgumentParser(
        description="Hermes 工作台一键安装自检脚本（六项检查，全中文输出）"
    )
    parser.add_argument(
        "--hermes-root",
        help="Hermes 根目录，优先级高于 HERMES_ROOT 环境变量（默认 %%USERPROFILE%%\\Desktop\\hermes-agent-main）",
    )
    args = parser.parse_args()

    hermes_root = resolve_hermes_root(args)
    localappdata = resolve_localappdata()

    print("===== Hermes 工作台安装自检 =====")
    print(f"Hermes 根目录：{hermes_root}")
    print(f"本地应用数据目录：{localappdata}")
    print()

    checks = [
        ("1. 网关", check_gateway),
        ("2. 防睡眠守护", lambda: check_keepawake(hermes_root)),
        ("3. 额度守卫", lambda: check_quota(hermes_root)),
        ("4. 看板库", lambda: check_kanban(localappdata)),
        ("5. 插件组件", lambda: check_plugins(localappdata)),
        ("6. 配置检查", lambda: check_config(localappdata)),
    ]

    statuses = []
    for index, (name, func) in enumerate(checks, start=1):
        status, message = func()
        statuses.append(status)
        print(f"[{index}/6] {name}：{status}")
        if message:
            print(f"      说明：{message}")

    print()
    print("===== 汇总 =====")
    print(
        "通过：{} ｜ 失败：{} ｜ 跳过：{}".format(
            statuses.count("PASS"),
            statuses.count("FAIL"),
            statuses.count("SKIP"),
        )
    )
    return 1 if "FAIL" in statuses else 0


if __name__ == "__main__":
    sys.exit(main())
