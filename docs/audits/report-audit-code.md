# 工作台核心代码只读深度审计报告（看板卡 t_fe8645e6）

## 审计元信息
- 日期：2026-10-12
- 审计范围（仅以下 4 个文件；同目录 *.bak-* 备份文件不读不审）：
  1. `C:/Users/<用户名>/AppData/Local/hermes/desktop-plugins/workbench-graph/plugin.js` — 1142 行 / 60145 B — sha256 前 12 位：`5e5e60c52b28`
  2. `C:/Users/<用户名>/AppData/Local/hermes/desktop-plugins/workbench-overview/plugin.js` — 384 行 / 13642 B — `f0332b958d76`
  3. `C:/Users/<用户名>/AppData/Local/hermes/desktop-plugins/workbench-field/plugin.js` — 84 行 / 2663 B — `7017faab6e2a`
  4. `C:/Users/<用户名>/AppData/Local/hermes/plugins/workbench-graph/dashboard/plugin_api.py` — 933 行 / 39834 B — `4ad33ee2d4ff`
- 方法：只读 + 逐行核对。仅用 Read/Grep/Glob 读取；未执行任何 shell 命令；未打开/读取任何凭据、密钥内容文件（本报告不含任何密钥真实值，仅描述变量名与行为）；未修改、重命名、删除任何既有文件。报告中每一处「文件:行号」均已用 Read 工具重新打开对应行段核对，行号以当前磁盘文件为准。
- 下文文件缩写：api = plugin_api.py（后端）；g = workbench-graph/plugin.js；o = workbench-overview/plugin.js；f = workbench-field/plugin.js。

## A. Top 10 问题（按严重度从高到低）

**1.【高·待人工核实】`/tasks`、`/summary` 的 board 查询参数无校验，直接透传 `connect_closing`**
- 位置：api:21、65-76、88-116（重点 66-72、96）
- 现象：`GET /api/plugins/workbench-graph/tasks|summary?board=...` 的 board 参数无白名单/格式/长度校验，原样传给 `kbc.connect_closing(board=board)`。若 `kanban_db_connect` 将 board 拼接进 sqlite 文件路径，`board=..%2F..%2F...` 可能打开任意 sqlite 库；即使仅影响 board 选择，也缺乏输入边界。
- 根因：`_BOARD_Q = Query(None, ...)`（21 行）只写了描述，无校验；tasks 的 66-72 行与 summary 的 96 行原样透传。
- 修复建议：进入 `connect_closing` 前校验 board 为 `^[A-Za-z0-9_-]{1,64}$`（或 None）；同时人工核对 `kanban_db_connect` 对 board 的路径处理（应 join 到 hermes home 后 normalize、拒绝 `..`）。
- 验证方法：构造 `GET /api/plugins/workbench-graph/tasks?board=..%2F..%2F<已知 sqlite 相对路径>` 观察是否返回非预期数据；需先人工核实 `connect_closing` 实现确认可复现性。
- 严重度：高——若 board 可穿越路径则能读取任意 sqlite 内容；因依赖函数不在审计范围，标注【待人工核实】。

**2.【中】`/wake` 的 path 参数未校验，直接作为启动参数传给 GUI 程序**
- 位置：api:876-894（重点 889-890）
- 现象：POST body 的 `path` 仅做 strip，不检查是否存在、是否为目录、长度，直接 `args.append(path)` 后 `Popen`。目标含 `trae-cn.cmd`/`trae-solo-cn.cmd` 等 cmd 启动器，以 `-` 或 `/` 开头的字符串可能被目标程序解析为选项（参数注入）；任意路径/超长字符串也会被原样传入。
- 根因：889-890 行 `if tgt[1] and path: args.append(path)` 无任何校验；`path` 的来源是请求体。
- 修复建议：仅接受「存在的目录」且为绝对路径（`os.path.isdir(path)` 且 `os.path.isabs(path)`），并限长（如 260）；或改为工作区目录白名单。
- 验证方法：`POST /wake {"agent":"trae","path":"--help"}` 观察 trae-cn.cmd 是否把 `--help` 当参数；传不存在的路径观察是否被拒绝。
- 严重度：中——本地 API、无 shell 拼接，注入面有限，但可被本机任意调用方利用。

**3.【中】`_trae_set_model` 直接改写运行中 Trae 的 sqlite 状态库（含全部工作区副本）**
- 位置：api:433-501（重点 455-468、472-501）
- 现象：直接 `UPDATE Trae CN/User/globalStorage/state.vscdb` 的 ItemTable，并遍历 `workspaceStorage/*/state.vscdb` 批量改写 sessionRelation 模型映射。若 Trae 正在运行：写入可能触发 `database is locked`、被 Trae 退出时覆盖，或破坏正在编辑的会话模型状态。
- 根因：docstring 自述 "Close Trae first for the write to stick"（434-435 行），但代码未检测 Trae 进程是否运行；455-467 与 477-497 行均直接连接 sqlite 写库。
- 修复建议：写前检测 Trae 进程（如 `tasklist` 匹配 Trae 可执行名），未关闭则返回提示「请先关闭 Trae」；对 workspaceStorage 的批量改写加 dry-run/确认，或改为只写主状态库并提示重启生效。
- 验证方法：开着 Trae 调用 `POST /builtin-model {"agent":"trae","model":"..."}` 观察是否报锁或重启后模型被还原。
- 严重度：中——可能破坏第三方应用状态，但异常路径被 try/except 兜住（500-501 行）。

**4.【中】`/task` 的 body 无长度上限、assignee 无白名单校验**
- 位置：api:285-306（重点 290-292）
- 现象：title 被截断到 200 字符（291 行），但 body 不截断（292 行），可写入任意大小的正文到看板库；assignee 任意字符串都会创建任务卡，拼错名字的卡片永远无人认领、堆积在队列里。
- 根因：290-292 行仅做 `strip()` 与 `title[:200]`，没有与已知 agent 名单（profiles）比对。
- 修复建议：body 加长度上限（如 2000）；调用前用 `profiles.list` 结果校验 assignee 存在于已知 agent 集合，非法则返回 `{ok:false}`。
- 验证方法：`POST /task {"assignee":"nobody","title":"t","body":"A"*100000}` 观察卡片是否创建、DB 是否膨胀；传不存在 assignee 观察是否被拒绝。
- 严重度：中——数据污染与资源滥用，非远程可利用（本地 API）。

**5.【中】claude-code 模型切换一次改写 6 个 env 键，且不校验模型是否真实存在**
- 位置：api:767-781（重点 773-775）
- 现象：同一个 model 被写入 `ANTHROPIC_MODEL`、`ANTHROPIC_DEFAULT_OPUS_MODEL`、`ANTHROPIC_DEFAULT_SONNET_MODEL`、`ANTHROPIC_DEFAULT_HAIKU_MODEL`、`ANTHROPIC_SMALL_FAST_MODEL`、`CLAUDE_CODE_SUBAGENT_MODEL` 全部 6 个键。若该模型在子代理/小模型角色上不可用，claude-code 后续运行可能报错或静默回退；与 qoder/workbuddy 分支不同，本分支写入前不检查 `_catalog_options` 目录。
- 根因：773-775 行无差别写 6 个键；765 行正则只防注入字符，不防语义错误。
- 修复建议：只写 `ANTHROPIC_MODEL`（其余键保留默认），或先校验 model ∈ `_catalog_options("claude-code", _CC_MODELS)` 再写。
- 验证方法：把 claude-code 模型设为目录外名字后运行 `claude -p` 观察报错；检查 settings.json 是否 6 键全被改写。
- 严重度：中——配置破坏可逆（用户可手动改回），但影响面覆盖 6 个角色键。

**6.【中·待人工核实】所有 API 端点无任何鉴权，本地任意进程/网页可调用**
- 位置：api:59-61、267-271、711-714、872-897、923-933（配合 612-634 的密钥使用）
- 现象：全部端点无 token、无 Origin/CORS 校验。若宿主把 FastAPI 绑定在 127.0.0.1 且无额外防护，本机任意进程或浏览器页面可：改写各软件配置（`/builtin-model`）、启动已注册应用（`/wake`）、读写 selection、触发 `/refresh-models`——而后者会用 settings/config 中读取的 API 密钥发起外部请求（612-634 行）。
- 根因：路由直接注册（19 行），无鉴权依赖；`_disc_cc`/`_disc_dsh` 读取本地凭据并外发。
- 修复建议：在宿主网关层加本地鉴权（如随机 token 请求头、Origin 白名单），或至少对写端点加 CSRF 防护。
- 验证方法：从任意本地 HTTP 客户端直接 POST `/api/plugins/workbench-graph/wake` 观察是否成功；需人工核实宿主的挂载与鉴权方式。
- 严重度：中——风险取决于宿主防护，本目录代码无法证实，标注【待人工核实】。

**7.【低】graph 页 selection 加载门闩期间存在「本地旧值覆盖服务器」竞态窗口**
- 位置：g:645-666（重点 653-666）
- 现象：挂载时 `GET /selection` 若返回空数组，661 行会用首次渲染闭包里的旧 `sel` POST 覆盖服务器；若用户在请求返回前已拖入/移出 agent，该旧值会短暂覆盖服务器，随后 645-652 行的 effect 才用新值纠正；GET 异步返回时组件可能已卸载，仍有写请求发出。
- 根因：653-666 行 effect 依赖 `[]`，闭包捕获首帧 `sel`；「服务器为空则回写本地」没有引用最新状态。
- 修复建议：用 ref 持有最新 `sel` 再 POST；或「服务器为空则上传」改为仅在用户确实改动过（dirty 标记）时上传。
- 验证方法：DevTools 限速网络后挂载页面并立即拖入 agent，观察 selection.json 是否先出现旧值再被纠正。
- 严重度：低——竞态窗口小且最终会自愈，但会造成短暂错误持久化。

**8.【低】`measureText` 的隐藏 SVG 从不清理，热重载会累积 DOM 节点**
- 位置：g:379-398（重点 382-391）
- 现象：`_mSvg` 被 `document.body.appendChild` 后从不移除；模块热重载重新求值会再建一个 SVG，旧节点残留（0×0 不可见但持续泄漏）。`fitText` 每截断一个字符调用一次 `measureText`，长名单下反复触发布局计算。
- 根因：391 行 appendChild 无配套 dispose；`_mSvg` 是模块级单例（379 行）。
- 修复建议：在插件 `onDispose` 里 `_mSvg.remove()`；`fitText` 改为二分查找或缓存测量结果。
- 验证方法：反复热重载插件后执行 `document.querySelectorAll('body > svg')` 观察数量递增。
- 严重度：低——泄漏节点极小，主要影响长期开发态（热重载）稳定性。

**9.【低】`/selection` 对 agents 类型不检查：字符串被逐字符拆开，16 上限静默截断**
- 位置：api:923-933（重点 925-926）
- 现象：`agents` 传字符串 `"trae"` 会被 `[str(a) for a in "trae"]` 拆成 `['t','r','a','e']` 持久化；超过 16 个 agent 被静默丢弃（`[:16]`）；agent 名未与已知软件 id 白名单核对，任意字符串可写入 selection.json。
- 根因：926 行 `[str(a) for a in (agents or [])][:16]` 假定 agents 必为列表。
- 修复建议：先 `isinstance(agents, list)` 校验，再逐个元素校验 ∈ `_EXTERNALS` 的 id 集合；超限返回错误而非静默截断。
- 验证方法：`POST /selection {"agents":"trae"}` 后 `GET /selection` 观察是否返回 `['t','r','a','e']`。
- 严重度：低——本地配置污染，影响参战名单正确性。

**10.【低】`_BAL_CACHE` 无锁，并发/refresh 竞态导致重复外部请求**
- 位置：api:128-129、250-271（重点 252-263、268-270）
- 现象：多个并发请求同时发现缓存过期，会各自调用外部 HTTP（DeepSeek/Anthropic）查余额；`refresh=1` 仅把 `t` 置 0（270 行），与读取存在竞态——刚写入的新缓存可能被另一个已穿透的请求再次覆盖计算。
- 根因：128-129 行缓存只有 `t`/`data` 两字段，无锁、无 in-flight 标记。
- 修复建议：加 `threading.Lock` 或 computing 标记，使并发 miss 只计算一次。
- 验证方法：并发发起 10 个 `/balances?refresh=1`，在 `_deepseek_balance` 临时加日志观察外部请求次数。
- 严重度：低——重复请求浪费配额，不产生错误数据。

## B. 硬编码清单（供「复刻包参数化」）
文件缩写：api / g / o / f（见头部）。

api:29 | `r"%USERPROFILE%\.claude\vscode-claude-code.cmd"` | claude-code 可执行候选路径（_EXTERNALS） | 改为配置项或运行时探测（`where claude`）
api:29 | `r"%APPDATA%\npm\claude.cmd"`、`r"%APPDATA%\npm\claude"` | npm 全局安装候选 | 同上（合并为 PATH 探测）
api:30 | `r"%LOCALAPPDATA%\Qoder CN\Qoder CN Launcher\Qoder CN Launcher.exe"` | Qoder 启动路径 | 参数化（安装位置可不同）
api:31 | `r"%USERPROFILE%\Desktop\Trae CN\Trae CN.exe"` | Trae 启动路径（桌面版） | 参数化（桌面/安装位置因机器而异）
api:32 | `r"%USERPROFILE%\Desktop\TRAE SOLO CN\TRAE SOLO CN.exe"` | TRAE SOLO 启动路径 | 参数化
api:33 | `r"%LOCALAPPDATA%\Programs\DeepSeek Harness\DeepSeek Harness.exe"` | Harness 启动路径 | 参数化
api:34 | `r"%LOCALAPPDATA%\Programs\WorkBuddy\WorkBuddy.exe"` | WorkBuddy 启动路径 | 参数化
api:138 | `~/.dsh/.credentials.yaml`（`os.path.join(expanduser("~"), ".dsh", ".credentials.yaml")`） | DeepSeek 凭据读取路径 | 参数化（跟随 Harness 数据目录）
api:143,173 | `https://api.deepseek.com/user/balance` | 余额查询外部端点 | 外部 URL 配置化（网关可替换）
api:160,189,505 | `~/.claude/settings.json`、`~/.claude/.credentials.json` | Claude Code 配置/凭据 | 参数化
api:201 | `https://api.anthropic.com/api/oauth/usage` | Anthropic 用量端点 | 外部 URL 配置化
api:314-315 | `_CC_MODELS = ["deepseek-flash[1m]", "deepseek-flash", "deepseek-v4-pro"]`、`_DSH_MODELS` | 内置模型兜底目录 | 模型目录：复刻时改为抓取/配置（已有 /refresh-models 抓取机制）
api:316 | `~/.qoder-cn/settings.json` | Qoder 配置路径 | 参数化
api:317-320 | `_QODER_MODELS`（Auto/Qwen3.8-Max/.../Qwen-3.8-Max 共 14 项） | Qoder 模型目录 | 模型目录：改为抓取/配置
api:321-323 | `_QODER_UUID_MAP`/`_QODER_UUID_REV`（含 2 个 UUID 常量） | settings.json model.name 的 UUID 映射 | 模型目录：随版本更新，改为抓取/配置
api:324 | `~/.codebuddy/settings.json` | CodeBuddy 配置路径 | 参数化
api:325-328 | `_CB_MODELS`（step-5-preview/.../auto 共 21 项） | CodeBuddy 模型目录 | 模型目录：改为抓取/配置
api:341-342 | `%APPDATA%\Trae CN\User\globalStorage\state.vscdb` | Trae 状态库路径 | 参数化（随 Trae 数据目录）
api:509 | `~/.dsh/profiles/{profile}/cordis.patch.yml` | dsh profile patch 路径 | 参数化（profile 名）
api:527 | 插件同目录 `model-catalog.json` | 模型目录缓存文件 | 建议移到 hermes home，避免插件更新被清空
api:586 | `%LOCALAPPDATA%\hermes\config.yaml` | 主配置 model 块来源 | 参数化（跟随 hermes home）
api:638 | `~/.qodersec/bin/qoderclicn.exe` | Qoder CLI 路径 | 参数化
api:656 | `%LOCALAPPDATA%\codebuddy\bin\codebuddy.exe` | CodeBuddy CLI 路径 | 参数化
api:865-868 | `_WAKE_TARGETS` 四组路径（Qoder CN Launcher.exe / trae-cn.cmd / trae-solo-cn.cmd / WorkBuddy.exe） | 唤醒目标 | 与 _EXTERNALS 合并为单一安装路径配置
g:46-50 | `MODEL_TIER`、`MODEL_FALLBACK = ['deepseek-v4-pro', 'deepseek-flash']` | 模型分层与兜底 | 模型目录：改为后端下发/配置
g:53-60 | `DRIVE`（claude-code/deepseek-harness/qoder/trae/trae-solo/workbuddy 的 auto/half） | 驱动类型映射 | 随 agent 配置下发
g:63-70 | `OWN_MODEL` 六条文案 | 自有模型显示文案 | 配置化（随软件版本变化）
g:73-80 | `CAPS` 六条能力文案 | 兜底能力卡文案 | 配置化
g:83 | `hermes.desktop.workbenchGraph.selection.v1` | localStorage 持久化键 | 一般无需参数化；多实例部署时加实例后缀
o:（全文件） | 无 | 无 | 无（Grep 扫描无机器特定路径/端口/URL，仅有应用内路由）
f:19-20 | `IDLE_MS = 12000`、`RETRIGGER_MS = 1000` | 空闲判定/重触发节流 | 非机器相关调参；产品化时可改为设置项

## C. 三条「必须保留的行为」（看似可疑、实则有意为之）

**C1. field 插件「默认静止、仅空闲才动」的省电策略**
- 位置：f:4-14（注释）、19-20、36-59、66-72
- 行为：启动后 12s 无交互才授予 `data-wb-idle` 让背景漂移；任何 pointer/wheel/key/touch 事件立即撤销并重新计时；鼠标离开窗口立即 hold 静止。
- 为什么是故意的：文件头注释给出本机 iGPU 实测数据（动画时 GPU ~50%+DWM ~25%，静止 ~19%/10%，移除 ~8%），并明确 "holds still BY DEFAULT and only drifts during idle windows"；注释还说明插件失效时应退化为永久静态背景（零成本）。
- 误改后果：改成默认常动或去掉 mouseleave 静止，低配 iGPU 上滚动掉帧；去掉 dispose 清理则热重载后事件监听叠加、定时器泄漏。

**C2. graph 插件隐藏窗口下的事件节流刷新**
- 位置：g:565-578（注释 565、572-573）
- 行为：`host.onEvent('*')` 全局事件以 2500ms 节流 invalidate 两个查询键（summary/profiles）；轮询 3s/10s 兜底。
- 为什么是故意的：注释 "A hidden Electron window throttles interval timers — gateway events keep the graph live"；且只失效事件真正改变的 key（opt-round 2026-10-09），避免无谓刷新。
- 误改后果：删掉事件驱动，隐藏窗口/后台时图表停留在旧数据；去掉节流则事件风暴导致请求洪峰。

**C3. 后端 `/wake`「只启动、不等待」，且无头通道直接返回成功**
- 位置：api:872-897（重点 874-875、878-879、894）
- 行为：`Popen` 后立即返回 ok，不 wait；claude-code/deepseek-harness 不启动任何进程直接返回 `ok + note`。
- 为什么是故意的：docstring 写明 "Headless agents are woken by the dispatcher itself — nothing to launch for them"；GUI 唤醒用 `DETACHED_PROCESS` 分离，避免 API 请求阻塞到应用退出。
- 误改后果：改成等待子进程会让 HTTP 请求挂起；给无头 agent 也启动进程会与 dispatcher 唤醒逻辑重复拉起。

## 附. 不确定点（只读审计无法定论，≤10 行）
- `kanban_db_connect.connect_closing` 对 board 的路径处理不在审计范围，路径穿越影响面【待人工核实】。
- 宿主对 FastAPI 是否有一层鉴权/CORS/Origin 校验，这 4 个文件无法证实。
- `_paged_ids` 的 `"&after_id="` 拼接在无查询串的 URL（`_disc_dsh` 的 `base+"/models"`）上会生成畸形分页 URL，但仅当端点返回 `has_more` 才触发；dsh 端点是否分页未知。
- g:1137 `ctx.i18n.onLocaleChange` 返回值未保存/未调用 dispose，若 SDK 不自动清理，热重载会累积监听（SDK 行为未知）。
- overview 插件未发现可确认的缺陷，故 Top10 未收录其问题。
- 前端 3 文件未发现 innerHTML/dangerouslySetInnerHTML 注入面（Grep 确认），未硬凑 XSS 条目。

[engine] claude -p headless · line refs re-read from disk · 自检：未执行 shell、未读凭据文件、所有行号均已 Read 回读核对、A=10/B=全文件扫描/C=3、正文≤400 行