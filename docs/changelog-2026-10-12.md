# 2026-10-12 深度检查与优化轮

本轮目标：对工作台做一轮「全面深入检查 + 优化」，随后把整个工作台整理为可复刻仓库。三路审计 + 修复全部完成并实测。

## 1. 三路审计（报告见 docs/audits/）

| 审计 | 执行引擎 | 产出 |
|---|---|---|
| 代码审计（claude-code 本体执行） | Claude Code CLI | `report-audit-code.md`（12k 字） |
| 守护脚本审计（deepseek-harness 本体执行） | dsh headless | `report-daemons.md`（20k 字） |
| 界面中文化审计（qoder 本体执行） | Qoder | `report-i18n.md`（7.5k 字） |

每张审计卡为**只读**、限时 30 分钟、报告末尾附「执行引擎声明 + 证据」。

## 2. 界面与插件修复

- `plugin_api.py`（看板后端）24 处：board 白名单 `^[A-Za-z0-9_-]{1,64}$` 在 API 边界直接 400；任务/选择/唤醒/内置模型/刷新模型全链路校验；余额轮询加双重检查锁 + 1800s TTL 缓存；异常详情只落盘（`logs/workbench-graph.log`），用户可见文案全中文。
- 桌面插件 18 处：`workbench-graph/plugin.js` 选区防抖（`selRef` 闭包修正）、`fitText` 二分、`ctx.onDispose` 释放 SVG；三个插件的名称/描述中文化。
- `agent-setup.md` 文案：`ready` → 「ready（就绪）」。

## 3. 守护脚本 v3.1（防睡眠 80/90/81）

- 单实例互斥（`Global\HermesKeepAwake80`，失败 fail-open）；
- 电源状态**属主戳**（pid+创建时间）+ 启动自修复：遗留 hold 而属主已死 → 自动还原；
- `--restore` 安全还原（活守护拒让、读回校验）；`90-keepawake.cmd stop/release` 已接线；
- powercfg 解析按「交流/直流」标签（含中文标签），退出码判定；备用 ES 机制保留；
- DB 连续读失败 ≥10 次降级为警告（宁可不睡，不可崩溃）；日志 2MB 轮转；壁钟漂移守卫（>600s 补一次 engage）。
- **实测**：`--once` busy/ac_sec=0 ✓；`stop` → 还原 300s（powercfg 读回）✓；`start` → v3.1 上线并重新 hold ✓。

## 4. 其它守护

- `73-wb-quota.py`：限免窗口 `FREE_WINDOWS`（step-5-preview →10-25、hy4 →10-31、hy3 →10-31）；过期模型永不被切到、在用过期模型自动移出；guard 退出码 0/3/2（网关掉线=3 且不改配置）；新增 `restore`。
- `88-watch-shutdown.py` v2：**仅 done/completed 触发**（blocked 不再触发）；宽限 45s 复查；关机前全局复查活跃卡；DB 失败不关机；被取消的倒计时**绝不自作主张重发**（2026-10-12 误关机教训）。
- `89-cancel-countdown.py` / `90 cancel-shutdown`：应急链路，实测可用（`shutdown -a` rc=1116=本无倒计时）。
- `codebuddy-gateway/supervisor.ps1` v2：**HTTP 健康检查**（`/v1/models` 200）代替「进程在=活着」；崩溃指数退避；停服走 `gateway.stop` 标记；日志 2MB 轮转；子进程树清理。
- `83-gateway-relaunch.ps1`：只按命令行精确匹配杀 Hermes 消息网关进程，且等其真正退出后再拉起 + 40s 内验证回位。

## 5. 本轮踩过的坑（已固化为规范）

1. **LF-only 的 `.cmd` 会被 cmd.exe 乱执行**（表现为每行开头被吃掉几个字符 + 流程串段）。修复：全部脚本统一 CRLF 并复查。
2. **`Get-CimInstance` 查询会匹配查询进程自身**（其命令行含匹配字样），曾导致「查杀脚本自杀、连带杀掉调用它的 bash」。修复：所有相关脚本加进程名白名单；持续任务改走 `.ps1` 文件（避免内联转义）。
3. 首次重启监管时出现**双监管打架**（旧实例残留占用 8787，导致新实例的子进程反复绑端口失败被误判「healthy→exited」循环）。修复：`restart-supervisor.ps1` 改为「杀旧（精确匹配）→ 等端口释放 → 清残留 → 只拉一个」，实测单实例稳定（200×3 探针 + 日志稳态）。

## 6. 本仓库

- 由上述优化后的实机状态整理：`config/`（脱敏）+ `daemons/` + `gateway/` + `plugins/` + `startup/` + `tools/` + `docs/` + `assets/`；
- 秘密扫描（sk-*/ghp_*/JWT/AUTH_TOKEN/长 Bearer 等）全库 0 命中；
- 推送：`git push` 经本机代理 `127.0.0.1:7877`（直连 GitHub 不稳）。

## 7. 全仓脱敏复核（2026-10-12 夜，PII 轮）

- 宽口径 PII 扫描（Windows 用户名 / GitHub 账号 / 邮箱 / MAC / 内网 IP / 手机号 / 密钥 / JWT / Bearer / QQ / 主机名），覆盖工作区与全部提交历史；
- 整改：`C:\Users\<用户名>` 路径占位化（100 个文件）、GitHub 账号名占位化；复查 0 残留；界面截图经逐张核验，无个人信息；
- 提交历史已重写（单条脱敏根提交）并强推，含旧标识的历史提交不再可达。
- 脱敏/扫描工具模板与报告随仓库提供：`tools/sanitize-pii.py`、`tools/scan-repo-pii.py`（复刻者把文件头 `WIN_USER`/`GH_USER` 改为自己的标识即可复跑）；终版扫描报告见 `docs/audits/repo-pii-scan-final.txt`，脱敏执行记录见 `docs/audits/sanitize-report.txt`。
