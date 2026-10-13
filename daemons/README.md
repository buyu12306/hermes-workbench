# daemons — 常驻守护脚本

> 部署位置假设：`<repo>\.build\workbench\`（`<repo>` = Hermes 安装目录，例：`C:\Users\<用户名>\Desktop\hermes-agent-main`）。
> 脚本中的绝对路径按此假设编写；换机时全局替换即可（`sed -i 's/C:\\Users\\<用户名>\\Desktop\\hermes-agent-main/<你的repo>/g'`）。

## 1. 防睡眠守护（任务感知）—— 80 / 90 / 81

**行为**：每 30s 判断「机器是否该保持清醒」。忙（有租约 lease、近期活动、agent 日志在写）→ 把 **AC 睡眠超时改成 0**；闲 → 还原为原始值（默认 300s）。这样笔记本在跑任务时进入不了睡眠，任务结束自动恢复省电。

- `80-task-keepawake.py` — 守护本体（v3.1）
  - 单实例：`Global\HermesKeepAwake80` 互斥量（拿不到则退出，防双开）
  - 属主戳：`%LOCALAPPDATA%\hermes\keepawake-power.json` 记录 `owner {pid, ctime, at}`；启动时**自修复**——发现遗留 hold 但属主已死则自动还原
  - `--once`：单次判断并打印 JSON（调试用：`python 80-task-keepawake.py --once`）
  - `--restore`：安全还原（拒绝在有活守护时抢占；读回原值校验）
  - 数据库连续读失败 ≥10 次自动降级为警告（宁可保持清醒，也不因此崩溃）
  - 日志 `%LOCALAPPDATA%\hermes\logs\keepawake.log`（2MB 自动轮转）
- `90-keepawake.cmd` — 控制台：`status | hold | release | start | stop | cancel-shutdown`
  - `stop` 会顺带执行电源还原（powercfg 读回校验）；`cancel-shutdown` = `shutdown -a` + 停掉 88 看护
- `81-keepawake-autostart.vbs` — 无窗口启动器（开机自启用；pythonw 路径/脚本缺失会写日志便于排查）

## 2. 模型额度守卫 —— 73

`73-wb-quota.py` 管理网关免费模型的**限免窗口**：

- `status` — 探测网关三个模型可用性 + 输出各自限免窗口（过期标 `⚠`）
- `guard --dry / guard` — 巡检：网关不可达 → 退出码 3 且**不改任何配置**；在用的模型窗口过期 → 自动切到窗口内的模型；连续 2 次配额类失败才切换
- `pick` — 打印当前应使用的模型（仅限窗口内）
- `restore` — 从状态文件回滚上一次切换
- 状态文件：`%LOCALAPPDATA%\hermes\codebuddy-gateway\quota-guard-state.json`

## 3. 关机看护 —— 88 / 89

- `88-watch-shutdown.py <task_id> [grace_min=40] [deadline_h=7]`：任务完成（**仅 done/completed**，blocked 不触发）后进入宽限；宽限期间每 45s 复查（卡被重开立即取消）；关机前**全局复查**是否还有 running/claimed 的卡；DB 读失败视为「不关机」。用 `QueryUnbiasedInterruptTime` 计清醒时长（睡眠时间不计入）。
- `89-cancel-countdown.py`：应急取消（`shutdown -a` + 按「进程名=python 且 命令行含 88-watch-shutdown.py」精确停掉看护）。

## 4. 其它

| 脚本 | 说明 |
|---|---|
| `87-watch-cards.py` | 卡片状态监听（无参数时打印用法并以码 2 退出） |
| `83-gateway-relaunch.ps1` | 重启 **Hermes 消息网关**：只杀命令行匹配 `hermes_cli main gateway run` 的进程（先等旧进程退出，再经 `Hermes_Gateway.vbs` 重启并验证） |
| `74-wb-fallback-setup.py` | 幂等写入 WorkBuddy 桥 fallback 链（hy4 → hy3 → deepseek），永不打印密钥（只打印指纹） |
| `70-keep-awake.ps1` / `9D-restart.ps1` / `91-keepawake-diag.py` / `94-keepawake-watch.py` | 防睡眠历史/诊断工具（新版用 80/90） |
| `82 / 85 / 86` | QQ 官方机器人：引导绑定 → 显示二维码 → 写入网关环境变量 |
| `84-wol-enable.ps1` | 启用网卡 Wake-on-LAN（备用） |

## 5. 两条硬教训（改脚本前必读）

1. **`.cmd` / `.vbs` 必须使用 CRLF 行尾**。某些文本工具会写出 LF-only 文件，cmd.exe 会把这种文件解析得面目全非（表现为「每行开头少了几个字符」的乱执行）。改完 `90-keepawake.cmd` 后建议校验：用 PowerShell `Get-Content -Raw` 或 `file` 命令确认 CRLF。
2. **杀进程要「按命令行 + 进程名白名单」双重匹配，且排除查询进程自身**。`Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'xxx' }` 会匹配到**正在执行这条查询的 PowerShell 自己**（它的命令行里就含有 `xxx` 字样），必须加 `$_.Name -match 'python(w)?\.exe'` 之类的进程名过滤，或 `-ne $PID` 排除自身；否则脚本会「自杀」甚至连带杀掉调用它的 shell。
