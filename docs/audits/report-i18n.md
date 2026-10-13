# 工作台自研界面层 · 中文界面审计报告（只读）

审计方法：逐个打开 5 个目标文件通读全文，并用脚本比对 i18n 字典 en/zh 键位（graph 106/106、overview 21/21，两侧键完全对称，无缺键回退），再按「界面是否真的渲染该文本」逐条核实行号后收录。
统计：表A 24 条 / 表B 10 条。
文件缩写：graph = `desktop-plugins/workbench-graph/plugin.js`；overview = `desktop-plugins/workbench-overview/plugin.js`；field = `desktop-plugins/workbench-field/plugin.js`；api = `plugins/workbench-graph/dashboard/plugin_api.py`；md = `workbench-graph/agent-setup.md`（路径根为 `C:\Users\<用户名>\AppData\Local\hermes\`）。

## 表A 应收录（英文残留）

| 文件:行号 | 现文案（原样摘录） | 建议中文 | 出现位置（角落/状态） |
|---|---|---|---|
| graph:897 | `name: 'Workflow Graph',` | `name: '工作流图',` | 插件管理页/插件列表里的插件名（全英文） |
| graph:898 | `description: '工作流图 — 你 → 总管 → 各 agent 的实时架构与任务流',` | 把「各 agent」改为「各智能体」 | 插件管理页插件说明行（中英混排，agent 未译） |
| graph:75 | `通道：dsh headless 全自动。` | `通道：dsh 无头全自动。` | 抽屉「能力描述」兜底文案（profile 无 description 时显示，DeepSeek Harness 卡 ⚙） |
| graph:201 | `throw new Error((r && r.error) || 'refresh failed')` | `'同步失败'`（或去掉兜底串，仅走 t('rmFail')） | 抽屉「更新清单」状态行：`更新失败：…refresh failed`（后端未回 error 时）存疑：仅异常分支可见 |
| graph:819 | `title: a.name` | `title: botTitle(a)` | 流程图内 agent 卡片 hover tooltip：显示内部 name（如 `claude-code`、`trae-solo`）而非中文名。存疑：name 属标识符，但同卡主标题已是中文 |
| graph:888 | `${t('updatedAt')} ${new Date(dataUpdatedAt).toLocaleTimeString()}` | `toLocaleTimeString('zh-CN', { hour12: false })` | 页面右下角页脚时间标记：可能渲染出 `7:46:03 PM` 式英文 AM/PM。存疑：取决于运行时 locale |
| graph:1007、1020、1025、1040、1054、1055、1056 | `你 → 总管 → 各 agent · 实时`；`还没有 agent——到「机器人」页签里创建`；`agent 领卡 · 点击打开看板`；`点击切换该 agent 的模型`；`已在图内 — 这些 agent 将参加下一次任务。`；`还没有 agent 参加本次任务 — 从右侧把软件智能体拖到这里`；`拖入的 agent 将参加下一次任务。` | 统一改「agent」→「智能体/软件智能体」（本文件 1048 行已用「软件智能体池」） | 页头副标题、看板池卡下方提示、空状态两行、模型切换 tooltip、图内计数注脚。存疑：术语一致性问题，非硬英文残留；1020 行 noAgents 当前未被渲染 |
| graph:76 | `计费：Qoder 账户 Credits。` | `计费：Qoder 账户积分（Credits）。` | 抽屉能力描述兜底（Qoder 卡 ⚙）。存疑：Credits 为软件内官方计量名 |
| field:63 | `name: 'Workbench Live Field',` | `name: '动态背景·空闲漂移',` | 插件管理页插件名（全英文） |
| field:64 | `description: 'Drifts the 动态背景 only during idle windows; holds it still while you use the app.',` | `description: '仅在空闲时段漂移动态背景；使用应用时保持静止。',` | 插件管理页插件说明（整句英文，仅「动态背景」为中文） |
| overview:323 | `name: 'Workbench Overview',` | `name: '工作台总览',` | 插件管理页插件名（全英文） |
| overview:324 | `description: '工作台总览 — bots, sessions, routines and quick jumps',` | `工作台总览 — 机器人、会话、例行任务与快捷跳转` | 插件管理页插件说明行（后半句纯英文） |
| api:294 | `"assignee 和 title 必填"` | `"任务负责人与标题必填"` | 抽屉派活：`派发失败：assignee 和 title 必填` |
| api:306 | `"error": type(e).__name__ + ": " + str(e)[:160]` | 中文兜底（如「建卡失败，请查看后端日志」），异常名转日志 | 抽屉派活失败提示后缀（现为 Python 异常英文名） |
| api:764 | `"agent 和 model 必填"` | `"软件与模型名必填"` | 抽屉「内置模型」下拉切换：`切换失败：agent 和 model 必填` |
| api:783、809、835、853、858、897 | `type(e).__name__ + ": " + str(e)[:120]` | 同上：改中文说明 + 异常细节入日志 | 抽屉状态行：`切换失败：…`、`唤醒失败：…` 之后直接跟英文异常串 |
| api:685、697、707 | `(type(e).__name__ + ": " + str(e))[:220]` / `[:160]` | 同上 | 抽屉「更新清单」：`更新失败：<英文异常名>: <英文消息>`，含写目录失败的 `_save` 分支 |
| api:882 | `"unknown agent"` | `"未知的软件智能体"` | 抽屉「唤醒软件」：`唤醒失败：unknown agent`（整条英文，用户直接可见） |
| api:885 | `"app not found: " + exe` | `"找不到启动程序：<路径>"` | 抽屉「唤醒软件」：`唤醒失败：app not found: C:\...`（英文前缀 + 路径） |
| api:154 | `"查询失败 " + type(e).__name__` | `查询失败（详见后端日志）` | 流程图/池卡「余额 …」角：DeepSeek Harness 卡显示 `查询失败 ReadTimeout` 式英文类名 |
| api:224、226 | `f"5h 剩 {max(0, round(100 - fiv))}%"`、`f"7d 剩 {...}%"` | `5小时窗口剩 X%`、`7天剩 X%` | Claude Code 卡「余额」角 + 抽屉余额行 |
| api:151、181 | `f"{i.get('currency', 'CNY')} {i.get('total_balance', '?')}"` | `¥5.00` / `人民币 5.00`（或至少「币种：人民币」） | 余额文本：`CNY 12.34`。存疑：ISO 货币代码是否算残留，请复核者裁决 |
| api:739 | `"current": cur or "Auto"` | `"自动"`（与 747 行 workbuddy 的 `"自动"` 保持一致） | 抽屉「内置模型」当前值。存疑：下拉选项 `Auto` 是写回 settings.json 的取值，不可改；仅兜底显示文本可中文化 |
| md:23 | `有 ready 的卡就照第三步领` | `有「ready（就绪）」的卡就照第三步领` 或 `状态为就绪（ready）的卡…` | 指令页正文第二步（用户复制给各软件的文本）存疑：ready 是 CLI 输出字面量 |

## 表B 保留英文（已确认）

| 条目 | 位置 | 保留理由 |
|---|---|---|
| 模型名 `deepseek-flash`、`deepseek-v4-pro`、`Qwen3.8-Flash`、`DeepSeek-V4-Pro`、`GLM-5.3`、`Kimi-K3`、`MiniMax-M2.7`、`step-5-preview`、`hy4-preview-f`、`space-bunny`、`Doubao-Seed-Code`、`deepseek-flash[1m]` | graph:47、50、64、66、304；api:314、315、317-320、325-328、421 | 模型名，且为写回各软件配置文件的字面取值，翻译会破坏功能 |
| 软件与品牌名 `Claude Code`、`Qoder`、`Trae`、`TRAE SOLO`、`DeepSeek Harness`、`WorkBuddy`、`SOLO`、`DeepSeek`、`Qwen` | api:29-34、181、184；graph:64、65、66、67、78；md:13、18 | 品牌/产品名，约定俗成不译（md:13 为看板名单身份标识）。注：`Hermes` 只出现在 import 与注释（graph:10、62），不进界面文本 |
| 命令行示例 `claude -p`、`dsh`、`qoderclicn --list-models`、`codebuddy --help`、`hermes.exe kanban assignees/list/claim/comment/complete/block`、`stat / ls` | graph:74、75；api:641、652、670；md:12、22、26、33、34、37、39、40 | 可执行命令，必须逐字保留 |
| 文件路径与文件名 `C:\Users\<用户名>\Desktop\hermes-agent-main\.venv\Scripts\hermes.exe`、`%USERPROFILE%\Desktop\Trae CN\...`、`settings.json`、`state.vscdb`、`cordis.patch.yml`、`model-catalog.json`、`selection.json`、`agent-setup.md`、`README.md`、`qoder-balance.json` | api:29-34、316、324、342、505、509、527、865-868；md:7、49、50、53、55 | 路径/文件名，不可译 |
| 配置键与环境变量名 `ANTHROPIC_BASE_URL`、`ANTHROPIC_AUTH_TOKEN`、`ANTHROPIC_MODEL`、`model.base_url/api_key`、`%LOCALAPPDATA%`、`uuid` | api:164-168、618、630、723、734-736、744、765、773-774；md:55 | 配置键名，用户在软件配置里要原样对照 |
| HTTP 端点与来源标识 `api.deepseek.com /v1/models`、`/models`、`codebuddy --help` | api:622、634、652、670（渲染于 graph:1087「清单来源：…」） | 技术端点标识，作为溯源信息保留 |
| 看板状态 token `triage/todo/scheduled/ready/running/review/blocked/done/archived` | graph:33-43；api:24、53、76 | 仅作数据键参与匹配；界面渲染走 st_* 中文标签（graph:1095），无需翻译 |
| 代码标识符与本地存储键 `workbench-graph`、`workbench-field`、`data-wb-idle`、`hermes.desktop.workbenchGraph.selection.v1`、`hermes-bots`、`wg-card` | graph:14、83、896；field:30、62；overview:21、111 | 插件 id/属性名/存储键，改动会破坏注册与持久化 |
| RPC 方法与请求字段 `profiles.list`、`profiles.configure`、`model.options`、`session.list`、`cron.manage`、`include_sessions` 等 | graph:441、471、589；overview:217、223、229 | 接口方法名，只进请求，不直接渲染为文本 |
| 通用技术缩写 `API`、`AI`（千问AI平台）、`IDE`、`ESM`、`SVG` | md:4；graph:74（AI）、77（IDE）、9（ESM）、340（SVG） | 业界通用缩写，中文界面惯例保留；graph:9、340 属代码注释，本就不入界面 |

## 中英混排但合理处（取舍说明）

- 中文为主、英文仅作技术标识的场合一律保留，不视为残留：
  - graph:1063 `已派发 ${id} · 约 1 分钟内自动开始` — `t_bd58f610` 类任务 id 必须原样。
  - graph:1050/292 拼接结果 `自有模型 Qwen3.8-Flash（千问网关）` — 品牌+模型名带中文注解，读感正常。
  - graph:1087 `清单来源：api.deepseek.com /v1/models · 更新于 2026-10-12 19:46` — 中文引导词 + 端点 + 本地化时间格式（`_iso_now` 用 `%Y-%m-%d %H:%M`，无英文月份）。
  - graph:1078 `内置模型已切换为 ${m}`、overview:119 的 `join(' · ')` 拼接结果 `DeepSeek-V4-Pro · 3 分钟前` — 同上。
  - api:618/630 `settings.json 缺 ANTHROPIC_BASE_URL/AUTH_TOKEN`、`主配置缺 model.base_url/api_key` — 中文句式 + 键名，保留。
  - api:879 `无头通道：派发即唤醒，无需打开界面`、245 `剩 420/1000`、244 `软件内查看·过期` — 已全中文。
  - md:3 `工作台用看板（kanban）给任务` — 首次出现括注英文原名，属合理混排。
- 已确认无需改动的英文区：三个 JS 文件顶部英文块注释（graph:1-9、overview:1-16、field:1-17）与散落英文行内注释/docstring（graph:565、572-573、765、1115；api:124-126、233-237、408、862、874-875），都不进界面，未入表。
- 纯数据字段（如 api 各 payload 里的 `"status": "login"/"inapp"/"local"`、`"launched"`、`"where"`）只进 JSON/日志、界面未渲染，未入表；其中 `where`（api:428、726、729、739、747）当前前端完全没用到，若后续渲染需一并中文化检查。
- 存疑项集中说明（请复核者裁决）：graph:201 兜底英文串、graph:819 tooltip 用内部 name、graph:888 时间本地化、graph:76 `Credits`、api:151/181 货币代码、api:739 `Auto` 兜底显示、md:23 `ready`。以上均已收录进表A（宁多勿漏原则）。
