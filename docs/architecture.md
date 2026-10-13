# 架构说明

## 1. 组件与职责

```
用户 ─► Hermes 桌面端（全中文界面）
          │
          ├─ 看板插件 workbench-graph（dashboard/, plugin_api.py）
          │     └─► kanban.db（tasks / task_comments / task_events）
          ├─ 桌面插件 workbench-overview / workbench-field
          ├─ 调度器：把卡片派发给六个软件智能体，回收状态与评论
          └─ Hermes 本体模型：DeepSeek（web 检索、监工、汇总）
```

- **调度只在 Hermes 侧**；真正干活的是六个软件本体。每张卡片在 `task_comments` 里声明执行引擎，用户按「软件自身执行 / Hermes 代执行」逐卡审计（硬性规则）。
- **看板即工作台**：任务生命周期 = 卡片状态机 `ready → running → done/blocked`（外加 `claimed`），事件流写入 `task_events`，产出物与评论写 `task_comments`。

## 2. 数据流

1. （用户/监工）建卡 → `tasks` 新增 row（board、title、body、assignee、engine）。
2. 调度把卡交给对应智能体（如 claude-code CLI / dsh headless / 桌面端自动化）→ 状态 `running`。
3. 智能体执行期间：日志写 `%LOCALAPPDATA%\hermes\kanban\logs\<task_id>.log`；关键节点回写评论。
4. 完成后回写 `done` + 报告路径 + 「引擎声明 + 证据」评论（工作台规范）。
5. 守护进程旁路观察同一批数据：
   - 防睡眠 80：租约/活动/agent-log 三个信号决定机器是否保持清醒；
   - 关机看护 88：指定卡片 `done` 且全局无活跃卡 → 延时关机；
   - 额度守卫 73：保证智能体用到的免费模型在限免窗口内。

## 3. 六个软件智能体（引擎归属）

| 智能体 | 调度方式 | 引擎（本体） | 凭据位置（本机） |
|---|---|---|---|
| claude-code | `claude` CLI（会话式/命令行） | 云知声 U2 Flash（限免，参考 `~/.claude/settings.json`） | `~/.claude/settings.json` env |
| deepseek-harness | `dsh.cmd --profile headless`（无头） | DeepSeek 账号 | `~/.dsh/.credentials.yaml` |
| qoder | 桌面端自动化 | Qoder 账号 | 软件内置登录 |
| trae / trae-solo | 桌面端自动化 | Trae 账号 | 软件内置登录 |
| workbuddy | 经本机网关 `:8787` | 腾讯限免三模型（+ fallback → DeepSeek） | 网关会话（`login_patient.py` 续期） |

## 4. 模型与压缩链（Hermes 本体）

- 主模型：`deepseek-flash`（provider `custom`，`api.deepseek.com`）
- 网关模型组：`wbgateway` → `http://127.0.0.1:8787/v1`（step-5-preview / hy4-preview-f / hy3）
- **辅助压缩**：`auxiliary.compression` 走 `wbgateway/step-5-preview`（1M 上下文、免费、超时 360s），失败回退 `deepseek-flash`；主配置与 6 个 profile 共 7 份均已改成同一策略（2026-10-12 实测）。
- WorkBuddy 桥的 **fallback 链**：hy4-preview-f → hy3 → deepseek-flash（`74-wb-fallback-setup.py` 维护）。

## 5. 文件与状态位置（本机）

| 路径 | 内容 |
|---|---|
| `%LOCALAPPDATA%\hermes\config.yaml` + `profiles\<六个>\config.yaml` | 全部配置（本仓库 `config/` 为脱敏副本） |
| `%LOCALAPPDATA%\hermes\kanban.db` | 看板数据库 |
| `%LOCALAPPDATA%\hermes\kanban\logs\` | 每张卡的执行日志 |
| `%LOCALAPPDATA%\hermes\logs\` | `keepawake.log / desktop.log / gui.log / gateway.log` 等 |
| `%LOCALAPPDATA%\hermes\plugins\workbench-graph\` | 看板插件包（dashboard 后端） |
| `%LOCALAPPDATA%\hermes\desktop-plugins\` | 三个桌面插件 |
| `%LOCALAPPDATA%\hermes\workbench-graph\` | 运行时文件（`agent-setup.md`、选型状态） |
| `%LOCALAPPDATA%\hermes\codebuddy-gateway\` | 本地网关（supervisor、会话、日志） |
| `<repo>\.build\workbench\` | 所有构建期/守护脚本（本仓库 `daemons/`+`tools/`） |
| `%LOCALAPPDATA%\hermes\keepawake-power.json` | 防睡眠的电源状态（属主戳） |

## 6. 工作规范（写卡/写脚本前先看）

- 界面语言：**全中文**，含角落小字；品牌名、模型名、协议名（MCP/SSE）、命令、路径、代码标识保持原文。
- 审计卡**只读**，不得修改任何文件；报告中的每个行号必须「写前重读一次源码核实」。
- 审计卡片收尾评论必须包含：执行引擎声明 + 报告绝对路径 + 统计证据。
- 单个审计卡限时约 30 分钟；报告长度上限：代码审计 ≤400 行、守护 ≤400 行、i18n ≤300 行。
- 杀进程、改配置这类高危操作：先备份（`*.bak-<日期>`），再做，再做后验证（编译 + 实跑 + 状态读回）。
