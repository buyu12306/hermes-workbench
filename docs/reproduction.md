# 从零复刻步骤

> 假设：Windows 11；`<用户名>` 为占位符，替换成你的 Windows 用户名。Hermes 安装目录 `<repo> = C:\Users\<用户名>\Desktop\hermes-agent-main`。
> 复刻时：把全文的 `<用户名>` 与 `<repo>` 替换为你机器上的实际值；脚本里的路径都是这两个前缀的组合。

## 0. 前置软件

| 组件 | 说明 |
|---|---|
| Hermes Agent 桌面端 | 提供 `hermes.exe`、桌面 UI、kanban、网关（消息通道） |
| Python 3.12 + venv | `<repo>\.venv`（脚本统一用 `.venv\Scripts\python.exe` / `pythonw.exe`） |
| uv | `C:\Users\<用户名>\.local\bin\uv.exe`（网关用；`uv run --with workbuddy2api` 免手装依赖） |
| Git + gh CLI | `%LOCALAPPDATA%\hermes\tools\gh\bin\gh.exe`（本机自带）；GitHub 操作如需代理见文末 |
| （可选）MyClash 等本机代理 | 本机 GitHub 直连不稳，仓库推送走 `127.0.0.1:7877` |

## 1. 配置（config/）

1. 拷贝 `config/config.yaml` → `%LOCALAPPDATA%\hermes\config.yaml`；
2. 拷贝 `config/profiles/*/` → `%LOCALAPPDATA%\hermes\profiles\`（六个软件目录）；
3. 把所有 `<YOUR_API_KEY>` 替换成你的真实密钥（主配置与 profile 里共 20 处）。

## 2. 六个软件本体（按用到的装）

| 软件 | 安装/登录 |
|---|---|
| Claude Code | 按官方方式安装 CLI；在 `~/.claude/settings.json` 配置 `ANTHROPIC_BASE_URL / AUTH_TOKEN / MODEL`（本机方案：云知声 U2 Flash，限免期） |
| DeepSeek Harness | 安装桌面端；无头模式：`"<app>\resources\runtime\cli\bin\dsh.cmd" --profile headless < prompt.txt`；凭据在 `~/.dsh/.credentials.yaml` |
| Qoder / Trae / Trae Solo | 桌面端安装并在软件内登录（额度/模型都随账号） |
| WorkBuddy | 桌面端安装；桥接由第 4 节网关提供 |

## 3. 插件（plugins/）

1. `plugins/workbench-graph/` → `%LOCALAPPDATA%\hermes\plugins\workbench-graph\`
   - `dashboard/` 内是看板插件后端（`plugin_api.py`、`manifest.json`、`model-catalog.json`）；
   - `agent-setup.md` / `qoder-balance-set.py` 同时复制一份到 `%LOCALAPPDATA%\hermes\workbench-graph\`（运行时目录）。
2. `plugins/desktop-plugins/<三个插件>/` → `%LOCALAPPDATA%\hermes\desktop-plugins\`。
3. 在 `%LOCALAPPDATA%\hermes\config.yaml` 确认 `plugins.enabled` 含 `workbench-graph`，并重启桌面端。

## 4. 本地网关（gateway/）

1. `gateway/supervisor.ps1`、`gateway/login_patient.py` → `%LOCALAPPDATA%\hermes\codebuddy-gateway\`；
2. `gateway/hermes-gateway-service/` → `%LOCALAPPDATA%\hermes\gateway-service\`；
3. 首次登录（会话缺失时）：`.venv\Scripts\python.exe gateway\login_patient.py`（浏览器/手机完成授权，最长等 1 小时）；
4. 启动监管：双击 `startup/CodeBuddy_Gateway.vbs`（无窗口；日志见 `codebuddy-gateway\supervisor.log`）；
5. 验证：`curl -H "Authorization: Bearer codebuddy-local" http://127.0.0.1:8787/v1/models` 返回 200。

## 5. 守护进程（daemons/）与开机自启

1. `daemons/` 全部脚本 → `<repo>\.build\workbench\`（路径与脚本内假设一致；必要时先全局替换路径）；
2. `startup/Hermes_KeepAwake.vbs`、`startup/CodeBuddy_Gateway.vbs` → `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\`；
3. 启动防睡眠守护：`<repo>\.build\workbench\90-keepawake.cmd start`（或直接重启登录）；
4. 检查：`90-keepawake.cmd status`（打印 busy 决策 + 守护存活 + 日志尾）。

## 6. 看板

首次打开桌面端使用「看板/工作台」视图时自动建库（`%LOCALAPPDATA%\hermes\kanban.db`）。后续建卡、派发、审计都在 UI 完成。

## 7. 验证清单（照做一遍）

- [ ] **一键自检（推荐先跑）**：`python tools/verify-install.py` → 六项 PASS / SKIP、退出码 0（有 FAIL 则退出码 1）
- [ ] `hermes gateway status`（消息网关在线；QQ 通道绑定后可收消息）
- [ ] `90-keepawake.cmd status` → 守护 RUNNING；忙时 `ac_sec=0`，`stop` 后恢复 300s
- [ ] `curl http://127.0.0.1:8787/v1/models` → 200（带 Bearer codebuddy-local）
- [ ] `python <repo>\.build\workbench\73-wb-quota.py status` → 三个模型状态 + 限免窗口
- [ ] `python 80-task-keepawake.py --once` → 输出 busy JSON（调试单次判断）
- [ ] 桌面端看板显示卡片、界面全中文（含角落小字）

## 8. 常见坑

- **代理**：本机 GitHub 直连不稳；git 推送建议走本机代理（`http.proxy=http://127.0.0.1:7877`），下载 GitHub release 资产用 `gh-proxy.com` 前缀。
- **CRLF**：`.cmd`/`.vbs` 必须 CRLF 保存（见 `daemons/README.md` 教训）。
- **杀进程**：一律「命令行 + 进程名白名单」双匹配，防止误杀桌面端/本体/自身。
- **密钥**：本仓库不含任何真实密钥；写入新配置后不要在聊天/日志中回显。
