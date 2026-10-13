# 工作台守护脚本与后台服务审计（只读）· 卡 t_02fde5cf

- 审计时间：2026-10-12 22:00–22:15（UTC+8）｜**只读**：未创建、修改、删除、结束任何被审文件或进程
- 审计对象：`.build\workbench\` 10 个脚本 + `codebuddy-gateway\supervisor.ps1` + 登录启动项 + 运行现场（进程/端口/日志）
- 交叉复核引擎：**DeepSeek Harness 本机通道**（`dsh headless`，见文末引擎声明与原始输出 `dsh-raw-audit.txt`）；本文中标注 ⊕ 的条目来自引擎复核补充，行号已由本人逐一复读核对
- 行号基准（md5 与 stat，复现用）：

| 文件 | 行数 | 字节 | mtime | md5 |
|---|---|---|---|---|
| 80-task-keepawake.py | 469 | 18240 | 2026-10-12 21:44:57 | bec5314084c740b5c0522dc6e87054b7 |
| 81-keepawake-autostart.vbs | 7 | 439 | 2026-10-11 02:57:11 | b77d589f8eda46c93e0893d773122205 |
| 90-keepawake.cmd | 61 | 3353 | 2026-10-12 21:30:37 | 1e6aa236ef576f8547d5232828a4d137 |
| 94-keepawake-watch.py | 106 | 4427 | 2026-10-12 21:44:57 | be74ec5ed5dccbb8667a31e4c5311ac9 |
| 73-wb-quota.py | 299 | 11666 | 2026-10-12 19:33:49 | b43b7103d4c83e3d198efa01075f1cd8 |
| 74-wb-fallback-setup.py | 92 | 3425 | 2026-10-12 19:33:49 | 290a326ed3aab4ce705e569d0531ae3c |
| 87-watch-cards.py | 61 | 2059 | 2026-10-11 16:09:23 | fc403474836aade8b6d8c57d761cc110 |
| 88-watch-shutdown.py | 76 | 2682 | 2026-10-12 09:21:55 | f1e272f40d24af7f1b2d6f152cac8dc1 |
| 89-cancel-countdown.py | 26 | 1207 | 2026-10-12 09:17:04 | 83890c5d14a7f858ee5f2b191fe955cb |
| 83-gateway-relaunch.ps1 | 14 | 758 | 2026-10-11 02:57:36 | 9d0253908b2c32ccf31e351d6dd9a54f |
| codebuddy-gateway\supervisor.ps1 | 21 | 942 | 2026-10-12 17:49:18 | 1a521ff76a9b7c0be57110ddc31035d2 |

运行现场实测（只读命令：`powercfg /query`、`netstat -ano`、`tasklist`、psutil 枚举）：

- AC 待机超时 **当前=0x00000000（0 秒）**，DC=0x000000b4（180 秒）→ daemon 的 hold 此刻生效中；`keepawake-power.json` = `{"applied": true, "ac_orig_sec": 300}`
- 守护链路：`pythonw.exe 368`（venv 重定向壳，exe=`.venv\Scripts\pythonw.exe`）→ `pythonw.exe 29500`（真解释器，exe=`C:\Users\<用户名>\.workbuddy\binaries\python\versions\3.14.8\pythonw.exe`）。**这是 1 个逻辑守护的 2 个 OS 进程**（venv 的 python/pythonw 是 redirector），不是双实例；`keepawake.log` 只有 29500 的自报 `daemon start`
- `netstat`：127.0.0.1:8787 LISTENING，PID 5848 = supervisor(18560) → uv(16944) → uv 环境 python(14564，壳) → 系统 Python3.12(5848，真进程)，**网关链路健康且单实例**
- 启动项：`Startup\Hermes_KeepAwake.vbs` 与 `81-keepawake-autostart.vbs` **md5 完全相同**（两份人工副本）

---

## 1. 80-task-keepawake.py —— 任务感知防睡眠守护 v3（469 行）

**职责**：每 30s（L80）采样一次"是否忙"（L315-388）：手动旗标、root/profiles 的 turn lease 与消息新鲜度、异步委派状态、agent.log 内容感知活性、kanban 任务 running/claimed、worker 日志 mtime；忙则 ①`SetThreadExecutionState` ES 保持（L446）②把 AC 待机超时改成 0（L226-252，L205-209）；闲则释放并把超时还原为 hold 前值（L255-266）。单实例命名互斥（L104/L391-402），`--once` 打印一次判定（L416-425）。

### 关键风险

- **R80-1（高）电源方案改动是持久化的全局状态，恢复链有三条但都非无条件**。被 TerminateProcess/taskkill /F/断电杀死时 atexit（L269-275, L436）不执行；剩余召回路径只有"下次 daemon 跑起来并走到 idle 分支"（L458）和人工 `90-keepawake.cmd :stop`（L60）。docstring L43-44 声称的"startup 自动修复陈旧 hold"**在代码里没有实现**——没有启动对账逻辑。⊕ 修复：启动时读 `applied` + owner(pid+启动令牌)，owner 不存在就强制恢复并留日志。
- **R80-2（高）释放路径用缺省 300 猜原值**（L261-263）：`ac_orig_sec` 缺失/非整数时 `orig=300`。若用户原本设的是"从不睡眠(0)"或 1200s，release 会把电源策略静默改成 5 分钟——**持久性策略篡改**。修复：原值不可得就不要写回（宁可不恢复），只告警；状态文件加来源/校验。
- **R80-3（高）json 丢失即失去回收能力**（L257-259）：`not applied` 时直接 return，而系统可能仍是 0 → 永不睡眠且无告警。修复：释放逻辑不要单点依赖 JSON；"无 owner 在跑 且 AC=0"就按最后已知值恢复。
- **R80-4（中）DB 故障被当作"忙"且无上限**（L348-349, L375-386，⊕）：任何 state.db/kanban.db 读取异常都进 reasons → 库被独占锁/损坏时机器永不睡眠、无告警升级。修复：连续 N 次错误降级为 warning，或给 fail-open 加时间上限。
- **R80-5（中）`powercfg` 只看 stdout，不看 returncode**（L179-187，⊕）：`_powercfg_set_ac_sec`（L204-209）把失败当成功；engage 路径有回读校验（L234/L249），**release 路径（L264）没有回读**。修复：判 `r.returncode==0`，release 后回读校验。
- **R80-6（中）释放前不与当前值比较**（L264，⊕）：会覆盖用户在 hold 期间手改的值（丢失更新）。修复：仅当当前值 == 本进程写入值时才还原。
- **R80-7（中）单实例守卫 fail-open + `Local\` 命名空间**（L397, L399, L402，⊕）：CreateMutexW 失败/异常都 `return True`；`Local\` 只在同一登录会话内互斥，服务/计划任务等另一会话启动的实例会并存并互相抢写同一份 `keepawake-power.json`（0↔300 抖动）。修复：`Global\`+SID 命名；创建失败时降级为"只监测不写系统设置"。
- **R80-8（低）AC/DC 解析脆弱**（L195-198，⊕）：`re.findall(r'0x...')` 取 `vals[-2]` 依赖输出里"恰好最后两个 0x 是 AC/DC"，中文/英文版式变化或多出十六进制就会读错；失败返回 None → 只剩 ES 兜底，而本机（Dell G15 / S0 Connected Standby）**ES 实测不阻止待机**（docstring L32-36 的内核证据）。修复：按标签解析或改用 PowerWriteACValueIndex API。
- **R80-9（低）日志与重复调用**：`log()`（L108-113）只追加无轮转（当前 keepawake.log 45 行/1.5 天，风险低）；`--once` 每次都会 query powercfg + 扫所有 profile DB（`90-keepawake.cmd status` 会调它）。

### 边界条件审查

- **重复实例**：v2+ 之间互斥有效（日志 15:56:41、15:57:25 两次 `duplicate instance detected` 实证）；跨版本残留进程不拦（R80-7）。实测本机 368/29500 是"壳+真进程"，**不是**重复实例——但要提醒：按命令行匹配做"实例计数"的脚本（如 90-keepawake.cmd）永远会数到 2 个 pid。
- **休眠恢复**：`tick % 20` 漂移守护（L461）是"循环次数"计时，睡眠期间不推进 → 醒来后最多要等 20 个 tick 才重申 0；若期间超时被外力改回，存在允许睡眠的窗口。修复：用"上次 engage 的墙钟时间戳"判定。
- **旗标竞态**：`keep-awake.on` 是硬理由且**无 TTL**（L323-325）→ 忘了删就是永不睡眠。修复：旗标内容写到期时间。
- **进程匹配误杀**：本文件不杀进程；匹配逻辑在 90-keepawake.cmd（见 R90-3）。
- **日志无限增长**：只在状态切换/告警时写，实测低风险；无轮转。
- **时钟回拨/跨天**：agent.log 解析用本地时间 `strptime(...).timestamp()`（L156）与 `time.time()` 同源，且 `0 <= now-ts <= 3600`（L159）挡住回拨与未来时间；lease 用 epoch 直接比较；跨天无影响。**结论：本项健壮**（唯一残留：`--once`/daemon 跨 DST 无影响，因用同源本地时间）。

### 修复建议（做法级）
1. 启动自检：`applied=true` 且 owner(pid+启动时间) 不存在 → 强制恢复到 `ac_orig_sec`（无值则只告警），写事件日志。
2. `_power_hold_release`：先比当前值再还原，还原后回读；`orig` 不可得时拒绝写回。
3. JSON 加 owner 字段（pid、进程启动时间、写入时刻），`--once` 与 daemon 都只读不写（现状 ✓，L278-279 注释已说明）。
4. 互斥锁改 `Global\HermesKeepAwake80-<SID>`；创建失败 → 只监测不写电源。
5. DB 错误 → 计数降级；keepawake.log 超 2MB 截断重开。

---

## 2. 81-keepawake-autostart.vbs（7 行）

**职责**：登录启动项里的窗口化启动器，用 venv 的 pythonw 拉起 80 脚本（L6 设工作目录，L7 启动）。

- **R81-1（中）3 处绝对路径硬编码**（L6；L7×2）：`.venv\Scripts\pythonw.exe`、`80-task-keepawake.py`、启动目录。venv 重建/仓库搬家 → wscript 静默失败（窗口模式 0，无报错窗口也无日志）→ **整个守护层消失**，正是"夜里睡掉半张卡"的成因模式。修复：加 `fso.FileExists` 前置检查 + 失败写日志；或改计划任务 + 启动对账。
- **R81-2（中）两份人工副本**：`Startup\Hermes_KeepAwake.vbs` 与 `81-keepawake-autostart.vbs` md5 相同（实测），但开机走 Startup 那份、`90-keepawake.cmd` 的 `:start/:hold` 走 .build 那份 → 改一份不生效的经典陷阱。修复：Startup 里放一个转调 .build 那份的 3 行 stub（如 Hermes_Gateway.vbs 的做法）。
- **R81-3（低）无存活指纹**：启动成功与否没有任何痕迹。修复：守护启动时写 heartbeat 时间戳，控制台 `status` 校验新鲜度。
- 边界：重复实例由 daemon 的 mutex 兜住 ✓（日志有据）；无日志增长；无时钟问题。

---

## 3. 90-keepawake.cmd（61 行）

**职责**：唯一运维控制面 `status|hold|release|start|stop`。

- **R90-1（高）`:release` 不恢复电源方案**（L46-49）：只删旗标。若此刻 daemon 已死（崩溃/上次 `:stop` 后未重启），系统仍停在"AC 永不睡眠"，而控制台会打印"auto resumes within 30s"——**误导性文案 + 不可逆状态残留**。修复：release 时若 `json.applied` 且无 daemon 在跑 → 复用 L60 的恢复片段。
- **R90-2（中）`:stop` 的补偿恢复依赖 json**（L59-60）：顺序正确（先硬杀再恢复，因为 Stop-Process 不给 atexit 机会）；但 json 缺失时只打印 `power state: no hold file` → **静默留下 AC=0**。修复：json 缺失时告警并提示手工核对/恢复。
- **R90-3（中）匹配式只看 `pythonw.exe`**（L34/L43/L55/L59）：若有人用 `python.exe` 前台调试跑同一脚本，`status` 会报"NOT RUNNING"且 `stop` 杀不到 → hold 泄漏。修复：`python(w)?\.exe` 且排除 `--once`。
- **R90-4（中）5 条绝对路径硬编码**（L13-17）：整卡与本机目录强绑定，复刻必改。
- **R90-5（低）`status` 的"pids"会显示 2 个**（L34）：venv redirector 壳 + 真解释器（实测 368/29500），容易被误读成双实例；注释里应写明。
- 边界：无循环、无自建日志、无时钟问题；进程匹配误杀风险低（`80-task-keepawake` 子串 + 仅 pythonw；但该子串也会匹配将来叫 `180-task-keepawake-*.py` 的脚本）。

---

## 4. 94-keepawake-watch.py（106 行）

**职责**：一次性观测量脚本——T+8/20/35/55/80 分钟各采一次快照（keepawake.log 尾部、agent.log 新旧、lease/kanban 状态、power json 与 AC 现值、电池报告里的睡眠记录），追加到 `cache\scratch\keepawake-watch.txt`。

- **R94-1（中）输出文件无锁、可重复启动**：实测本机正有 1 个实例在跑（21:46 启动，进程链含 3 层 bash 包装）。追写同文件（L93-94）且每次采样都 `powercfg /batteryreport` 重写同一个 `battreport.html`（L21,L28）→ 并发时会交错写入/读到半写文件（解析失败被 L36-37 静默吞成一行 ERR，证据失真）。
- **R94-2（中）电池报告解析不可靠**（L30-35）：正则依赖 HTML 版式与 `[^<]*` 单层单元格；**实测本次最后一段 "recent machine state transitions" 为空**（解析没取到任何行），而同一时间 `battreport.html` 有 79792 字节。用它做"机器是否真睡过"的结论需要先修解析。修复：改用 `powercfg /systemsleepdiagnostics` 或事件日志（Kernel-Power 506/507）。
- **R94-3（低）全量读 agent.log**（L69）：当前 3.7MB，每次采样全量读一次（5 次）→ 应 seek 尾部。
- **R94-4（低）标签与实际时间可能不符**（L98-104）：`time.sleep(720/900/1200/1500)` 在系统睡眠期间不推进，而 elapsed 用 `time.time()` 计算 → 标签写 T+20 时实际可能是 T+400。
- 定位：**一次性观测工具**，不适合进复刻包（它观测的机制本身要重做）。

---

## 5. 73-wb-quota.py（299 行）

**职责**：三个限免模型（step-5-preview / hy4-preview-f / hy3）的额度守卫：经本地网关探测可用性；不可用时把 worker（`hermes -p workbuddy config set model.default`，L138）或引擎（`~/.codebuddy/settings.json`，L161/L173-178 原子写）切到下一个可用限免模型；另有 `pick` 给派卡取模型名。

- **R73-1（高）`quota_like` 判定被算出但从未使用**（L118-119 产出，L230-253 只看 `ok`）：任何非额度类失败（网络抖动、500、模型名错、75s 超时）都会触发**真实写配置**。修复：要求 `quota_like=True` 或连续 N 次失败才切。
- **R73-2（高）限免窗口写在注释里，代码不校验日期**（L42-46：10-12→10-25、14 天试用、每日免费至 10-31）：窗口一过，guard 仍会把两个软件智能体切到**已开始计费**的模型，直接产生费用。修复：窗口结构化（`{model:(start,end,kind)}`），过期即拒绝切换并告警。
- **R73-3（中）单向切换、无回切**：一旦切走，原模型恢复也不回切；`guard` 全部失败时返回 0（L267-272）→ 自动化调用方无法区分成败。修复：加 `restore` 子命令；失败返回非 0。
- **R73-4（中）探测成本与时长**：每模型最多 2 次 chat completion（L91-101），最坏 3×2×75s≈7.5 分钟；`status` 也会对 3 个模型各探一次（L197-198）。
- **R73-5（低）无并发锁**：两个 guard 同时跑会互相覆盖配置；`AUTH=Bearer codebuddy-local`（L40）明文但绑 127.0.0.1（L39，可接受）；`quota-guard.log` JSONL 无轮转（当前 178B）。
- 定位：**若复刻包保留"免额模型通道"，它是必需组件（定时任务）；否则可弃**。参数化见最后一节。

---

## 6. 74-wb-fallback-setup.py（92 行）

**职责**：一次性把 workbuddy profile 的 `fallback_providers` 换成 `hy4-preview-f@gateway → hy3@gateway → deepseek-flash@api.deepseek.com(付费)`，并把 hy3 加进 `providers.custom.models`。

- **R74-1（中）把主配置的 DeepSeek key 复制进第二个配置文件**（L38 读，L57 写）：密钥面 1→2 个文件（另加 `.bak-quota-20261012`）；只打印指纹（L85）这点做得对。修复：改用环境变量/密钥引用，避免落盘复制。
- **R74-2（中）链尾付费且与主工作台同一把 key**：三个限免全挂时自动烧钱，且无日限额熔断。
- **R74-3（低）备份一次性且带日期**（L23）：重跑不刷新备份；不过整体替换链（L51-58）本身幂等，并有 round-trip 校验（L73-88）✓。
- **R74-4（低）前置校验不足**：`WB_CFG` 不存在时 `shutil.copy2`（L43-44）直接 traceback。
- 定位：**一次性开发工具**（判断依据：docstring 自述 one-shot；写的是"目标状态"而非常驻行为；有日期备份）。复刻时应把它降级成"目标状态说明 + 校验脚本"。

---

## 7. 87-watch-cards.py（61 行）

**职责**：只读轮询 kanban.db（90s 一次，L60），直到指定卡进终态，供 `terminal background=True, notify=True` 用。

- **R87-1（中）结论只走 stdout**（L51-54）：无落地文件；启动它的会话/进程一死，监控**静默消失**且没有痕迹。修复：写 JSONL 证据文件；或直接依赖 dispatcher 的看板通知（本卡判断：与看板自身通知重复）。
- **R87-2（中）默认卡号硬编码且已过期**（L19：`t_e704118f t_9423111b`）：不给参数就盯两张旧卡，3 小时后打印 TIMEOUT（无害但浪费一个进程）。
- **R87-3（低）无单实例**；`hours` 只认末尾纯数字（L17）；DB 打开正确（L14 用的是 live DB，注释已警告 decoy ✓）。
- 边界：DB 只读 ✓；deadline 用 time.time（休眠只影响超时判定，无副作用）；无日志文件增长。
- 定位：**一次性/临时工具**（看板通知已覆盖它的用途）。

---

## 8. 88-watch-shutdown.py（76 行）—— 风险最高

**职责**：盯一张卡，进终态后等 40 分钟（L16/L69-71）自动关机；或"清醒累计"超 7 小时（L17/L73-75）保底关机。

- **R88-1（严重，有实测事故）**：`shared\minidayz\shutdown-supervisor.log` 末行 = `2026-10-12 09:15:37 SHUTDOWN -> deadline 7.0h reached, status=running` ——**任务还在 running 时走到了期分支并真的执行了关机**（当时的版本还没有 L63-67 的空档过滤；09:17 才写了 89 应急取消、09:21 才给 88 打补丁）。当前代码的到期分支（L73-75）**依然不看任何状态**：任何超过 7 小时的活都会被腰斩。修复：到期前必须复查全局（`status IN ('running','claimed')` 或存在活跃 lease），有活则顺延而非关机。
- **R88-2（高）终态集合含 blocked**（L21）：`blocked`（等人决策/审批）被当成"可以关机"，恰好是最不该关机的状态。修复：只有 `done/completed` 才算成功完成，其余需显式开关。
- **R88-3（高）宽限期内不复查**（L69-71）：`time.sleep(GRACE_MIN*60)` 盲等 40 分钟，卡被重开/重试也照关。修复：宽限期内每 30-60s 重查，状态离开终态即取消。
- **R88-4（高）`-f` 强杀**（L44 `shutdown.exe -s -f -t 90`）：直接丢未保存工作；且发出后 `check=False` 不复核、随后 `sleep(600)` 退出（L47-48）→ 若被 `shutdown /a` 取消，守护静默结束、保底彻底失效。修复：去 `-f`；确认关机已被接受；取消后继续监控而非退出。
- **R88-5（中）空档过滤方向性缺陷**（L63-67）：只过滤"单次 >300s"的间隔。本机是 S0/Connected Standby（每几分钟醒一次，内核已证），多个 <300s 的睡眠间隔会被**累加成"清醒"**，用睡眠时间凑满 7 小时 → 深夜自动关机。修复：用 `QueryUnbiasedInterruptTime` 或唤醒事件算真实清醒时长。
- **R88-6（中）DB 报错/任务不存在都会走到期关机**（L31-38）：`dberr:*`/`missing` 都不在 TERM 里 → 永不进终态 → 7 小时后照样关机（库里根本没有任务在跑）。修复：这两类单独处理——持续错误只告警并暂停计时，任务确认不存在则立即退出。
- **R88-7（中）日志路径跨项目硬编码 + import 期就 open**（L20, L23）：指向 `工作区\Hermes工作台\shared\minidayz\`，目录缺失/搬家 → 启动即崩（对关机守护属"安全失败"，但没人会知道守护已经不在）。无轮转（当前 195B）。修复：路径参数化 + 降级到 `%LOCALAPPDATA%` + 心跳。
- **R88-8（中）无单实例/跨任务互斥**（⊕）：两个 watcher 各算各的，B 卡的到期会关掉 A 卡正在跑的机器。修复：命名互斥 + 关机前校验全局活跃度。
- **R88-9（低）时钟**：awake 用 `time.time()` 差值；回拨会让 `step` 变负、`awake` 倒退（deadline 被推迟，偏保守）。可接受。
- 定位：**建议不复刻**——"任务完成/超时自动关机"与本工作台"长夜连续跑卡 + 多智能体并行"的定位冲突，且已有一次实测误关机。

---

## 9. 89-cancel-countdown.py（26 行）

**职责**：紧急取消关机倒计时（`shutdown /a`，L10/L22）+ 终止 88 守护。

- **R89-1（高）按硬编码 PID 杀进程**（L16 `taskkill /F /PID 238852`）：该 PID 早已不存在；Windows 会复用 PID，将来若恰好被别的进程占用就是**误杀无关进程**。修复：按命令行匹配（`88-watch-shutdown`）定位，`shutdown /a` 保留。
- **R89-2（低）**两次 `shutdown /a` 幂等 ✓；无日志、未参数化。
- 定位：**一次性应急工具**；但"取消关机 + 按名终止 88"应固化进常规控制台（这也说明 88 的危险性）。

---

## 10. 83-gateway-relaunch.ps1（14 行）

**职责**：按命令行匹配杀网关，再经 VBS 重启。

- **R83-1（中）杀完只睡 2 秒就重启、且不验证结果**（L12-13）：旧进程若仍占端口/仍在写 state.db，新进程可能起不来；没有任何端口/心跳校验，失败静默。修复：轮询端口释放（≤15s）→ 启动 → 轮询 listening/心跳 → 失败告警。
- **R83-2（中）会杀掉所有匹配进程但只重启一个**（L3-11）：实测 `hermes_cli.main gateway run` 当前有 11596(父)/16668(子) 两个进程（同一 Popen 链）；如将来多 profile 各起网关，本脚本会全杀而只拉一个。
- **R83-3（低）硬编码 VBS 路径**（L13）；匹配正则依赖 `-m hermes_cli.main gateway run` 形态（实测吻合 ✓）。
- 旁证：`logs\gateway-exit-diag.log` 连续出现 `gateway.previous_unclean_exit`（最近一次：pid 16668 于 10-12T10:41Z 启动，前身 7020 的最后心跳 10:39Z）→ 与"硬杀 + 立刻重启、无优雅退出"的路径一致。
- 定位：**运维脚本**（复刻保留，需参数化）。

---

## 11. codebuddy-gateway\supervisor.ps1（21 行）

**职责**：每 30s 看 8787 是否 Listen（L11/L18-20），不在就 `uv run --with workbuddy2api python -m codebuddy_proxy …`（L15）拉起；`gateway.stop` 文件可让它退出（L10）。

- **R11-1（高）健康判定只看端口**（L11-12）：进程活着但卡死/不响应 HTTP 时永不重启；端口被**别的**进程占用时它反而认为"健康"。修复：HTTP 探活（GET /v1/models + 超时）+ 记录子进程 pid。
- **R11-2（高）无退避、无熔断**（L15-17）：子进程秒退时每 ~10s 重启一次，热循环并持续刷 `server.out`/`server.err`（`>>` 追加，无轮转，L4-5/L15）。修复：指数退避（10s→5min）+ 最大重试 + 熔断告警 + 日志轮转。
- **R11-3（中）`Get-NetTCPConnection` 的错误被 `SilentlyContinue` 吞掉**（L11，⊕）：查询失败返回 `$null`= "没在监听" → 盲目重复拉起。修复：区分"查询失败"与"未监听"。
- **R11-4（中）supervisor 自身无守护、无心跳**（⊕）：只有一句 `W "gateway not listening; starting"`；进程若死（当前实测 17:49 那次的 supervisor 已不在进程表里，只剩 18:41 那个）没有任何机制拉起它，也没有"启动成功"证据。修复：写心跳 + 成功/失败事件；如需常驻再加一层看护。
- **R11-5（中）`stop` 标志只在循环顶部检查**（L10，⊕）：大部分时间阻塞在 `uv run`，停机最长要等子进程退出；标志文件不删除 → 下次启动立即自杀。修复：收到停止主动终止子进程；退出时删除/归档标志。
- **R11-6（低）未切工作目录**（L15，⊕）：`& $uv run` 用调用者 cwd；`--with workbuddy2api` 是从索引/cache 解析包（实测真进程来自 uv 缓存），故暂判不致命，**待确认**。修：`Set-Location $dir` 或 `uv --directory`。
- **R11-7（低）`Add-Content` 未指定编码**（L7，⊕）：Windows PowerShell 5.1 按 ANSI 写入，非 ASCII 内容会乱码；全部路径/端口/解释器硬编码（L1-6, L11, L15）。
- 边界：重复实例（Startup 只一个入口，手工再跑就有两个 supervisor，无 mutex）；休眠（wall-clock 循环，无副作用）；旗标（见 R11-5）；日志（见 R11-2，当前 supervisor.log 214B / server.out 810B / server.err 1.8KB / proxy.jsonl 26KB）；时钟（无）。

---

## 12. 复刻包建议

### ① 必需组件 vs 一次性开发工具

判断依据（三条同时看）：**(a) 是否常驻或被开机/登录自动拉起；(b) 缺失是否会导致"不可逆后果或整段时间的连续工作失效"；(c) 是否被其它脚本/自动化调用（是别人的依赖）**。

**必需组件（必须复刻，且必须参数化）**

| 脚本 | 依据 |
|---|---|
| 80-task-keepawake.py | 常驻守护（a）；缺了则卡跑到一半就睡（b，已发生过）；被 81/90 依赖（c） |
| 81-keepawake-autostart.vbs | 开机自启入口（a）；它是"守护存在"的唯一保证（b） |
| 90-keepawake.cmd | 唯一运维控制面（c）；hold/stop/release 是人工兜底通道（b） |
| codebuddy-gateway\supervisor.ps1 | 常驻服务守护（a）；缺了本地免额模型通道整条断（b）；73 的探测依赖它（c） |

**次必需（运维动作，非常驻，建议保留但合并进控制台）**

- 83-gateway-relaunch.ps1：网关重启的"正确姿势"（按命令行匹配），可从 90 那种控制台脚本里调用。
- "取消关机"能力：把 89 的 `shutdown /a` + 按名终止 88 固化进控制台（**不要**保留硬编码 PID）。

**一次性开发工具（不复刻；复刻时只保留其"目标状态"或结论）**

| 脚本 | 依据 |
|---|---|
| 94-keepawake-watch.py | 固定 T+8…80 的观测日程（一次实验）；解析电池报告不可靠（实测为空）|
| 87-watch-cards.py | 与看板自身通知重复；无落地证据文件；默认卡号是历史卡 |
| 74-wb-fallback-setup.py | docstring 自述 one-shot；写的是"目标状态"；备份带日期 |
| 89-cancel-countdown.py | 单一事故的应急脚本（硬编码 PID 已失效）|
| 88-watch-shutdown.py | **建议不复刻**：定位与"长夜连续跑卡"冲突，且有实测误关机记录（09:15:37 status=running）|
| 73-wb-quota.py | **边界情形**：若保留"免额模型通道"则它是必需组件，但形态应改为**定时任务**（非守护），且必须先修 R73-1/R73-2 |

### ② 必需脚本里需要参数化的硬编码值（文件:行号 + 原值）

**80-task-keepawake.py**
| 行号 | 原值 | 建议参数 |
|---|---|---|
| L70 | `os.environ.get('LOCALAPPDATA', r'C:\Users\<用户名>\AppData\Local')` | 去掉个人路径回落，改用 `%USERPROFILE%\AppData\Local` 或必填环境变量（⊕） |
| L80 | `INTERVAL = 30` | 采样间隔（秒） |
| L81 | `RECENT_WINDOW = 150` | "忙"的时间窗（秒） |
| L82 / L83 | `ACTIVE_DELEGATION_STATES` / `KANBAN_BUSY_STATES` | 忙状态集合（跟看板 schema 走） |
| L92–99 | `AMBIENT_RE` 六条日志短语（`MCP servers reconciled with config` 等） | 环境相关的噪音过滤表，应外置成配置（Hermes 版本升级即失效） |
| L100 / L101 | `AGENTLOG_MAX_BYTES = 150_000` / `AGENTLOG_MAX_LINES = 500` | 尾部读取窗口 |
| L104 | `_MUTEX_NAME = 'Local\\HermesKeepAwake80'` | 互斥名（建议 Global + SID；R80-7） |
| L159 | `0 <= now - ts <= 3600` | agent.log 时间窗（1 小时） |
| L192, L205 | `SCHEME_CURRENT / SUB_SLEEP / STANDBYIDLE` | 电源方案与子项（GUID 化） |
| L198 | `int(vals[-2], 16)` | AC/DC 取值策略（改按标签解析，R80-8） |
| L261, L263 | 兜底 `ac_orig_sec = 300` | **默认恢复值（最危险，建议改为"不写回"）** |
| L461 | `tick % 20 == 0` | 漂移守护周期（次） |

**81-keepawake-autostart.vbs**
| 行号 | 原值 | 建议参数 |
|---|---|---|
| L6 | `sh.CurrentDirectory = "C:\Users\<用户名>\AppData\Local\hermes"` | 数据根（`%LOCALAPPDATA%\hermes`） |
| L7 | `"...\hermes-agent-main\.venv\Scripts\pythonw.exe"` + `"...\.build\workbench\80-task-keepawake.py"` | 解释器与脚本绝对路径（建议由安装脚本生成该 vbs，而不是手改） |

**90-keepawake.cmd**
| 行号 | 原值 | 建议参数 |
|---|---|---|
| L13 | `PY=...hermes-agent-main\.venv\Scripts\python.exe` | venv 路径 |
| L14 | `SCRIPT=...\.build\workbench\80-task-keepawake.py` | 守护脚本路径 |
| L15 | `VBS=...\.build\workbench\81-keepawake-autostart.vbs` | 启动器路径 |
| L16 | `FLAG=%LOCALAPPDATA%\hermes\keep-awake.on` | 旗标路径 |
| L17 | `LOG=%LOCALAPPDATA%\hermes\logs\keepawake.log` | 日志路径 |
| L34/43/55/59 | `$_.Name -eq 'pythonw.exe' -and $_.CommandLine -match '80-task-keepawake'` | 进程匹配规则（改 `python(w)?`，并注意 redirector 会数出 2 个 pid） |

**codebuddy-gateway\supervisor.ps1**
| 行号 | 原值 | 建议参数 |
|---|---|---|
| L1 | `$dir = "C:\Users\<用户名>\AppData\Local\hermes\codebuddy-gateway"` | 服务目录 |
| L2 | `$uv = "C:\Users\<用户名>\.local\bin\uv.exe"` | uv 路径 |
| L11 | `Get-NetTCPConnection -LocalPort 8787` | 监听端口 |
| L15 | `uv run --with workbuddy2api python -u -m codebuddy_proxy --host 127.0.0.1 --port 8787` | 包名/模块名/bind 地址/端口 |
| L17 / L19 | `Start-Sleep -Seconds 10` / `-Seconds 30` | 重启退避与轮询间隔（建议改指数退避 + 上限） |
| L4–L6 | `server.out` / `server.err` / `proxy.jsonl` | 日志路径与轮转策略 |

**73-wb-quota.py（若保留）**
| 行号 | 原值 | 建议参数 |
|---|---|---|
| L37/L38 | `HOME`（LOCALAPPDATA\hermes）、`REPO`（USERPROFILE\Desktop\hermes-agent-main） | 数据根/仓库根 |
| L39/L40 | `GATEWAY = http://127.0.0.1:8787/v1`、`AUTH = "Bearer codebuddy-local"` | 网关地址与令牌（改环境变量/密钥库） |
| L41 | `FREE_ORDER = ["step-5-preview","hy4-preview-f","hy3"]` | 限免模型清单（外置为带窗口的数据） |
| L42–46 | 窗口注释（`10-12→10-25`、`14天试用`、`每日免费至 10-31`） | **过期时间必须进入代码判定（R73-2）** |
| L47–L51 | worker 配置、引擎 settings、两个 exe 路径、`quota-guard.log` | 路径与日志 |
| L52 | `PROBE_TIMEOUT = 75` | 探测超时 |
| L54–57 | `QUOTA_MARKERS` 正则 | 额度类错误码（腾讯侧变更即需更新） |
| L138 | `hermes.exe -p workbuddy config set model.default <m>` | 目标 profile 名 |
| L161 | `codebuddy.exe config set -g model <m>` | 引擎可执行文件 |

---

## 附录：不确定点与未取证项

1. **88 事故链的完整时序**：日志只留下 `SHUTDOWN -> deadline … status=running` 一行的硬证据；"是否被 89 成功取消（未真正断电）"只能从 keepawake.log 09:18:59 的 `daemon start` 间接推断，**未找到关机/取消的系统事件记录**（未取 Windows 事件日志）。
2. **73/74 的实际额度状态**：本次未执行 `73-wb-quota.py`（它会向网关发真实 chat completion 探测，属"写"外部服务且可能计费），因此"当前限免窗口是否仍有效"未实测——请以卡外人工核验为准。
3. **supervisor R11-6（cwd）**：uv 从索引/cache 解析包，cwd 是否影响启动未实测（只做了静态判断）。
4. 本文所有行号均以第 1 节表格中的 md5 版本为准；文件一旦被编辑，行号需重新核对。
5. 审计期间**未修改任何文件、未结束任何进程**；控制台命令全部为只读（`powercfg /query`、`netstat -ano`、`tasklist`、psutil 枚举、`md5sum`、`stat`）。
