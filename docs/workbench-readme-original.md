# Hermes工作台 · 共享工作区

本目录是**所有软件智能体 + 总管（Hermes）的共享工作区**（位于你个人 `工作区\` 内的独立子文件夹，不影响其他项目）。
任务的调度与状态在「工作台 → 看板」里；**产物都集中到这里**。

## 目录

```
Hermes工作台\
├─ README.md      ← 本文件（规则以最新版为准）
├─ tasks\         ← 每个任务一个子目录：<task_id>\
└─ shared\        ← 跨任务的公用素材
```

## 对所有 agent 的规则

1. **取任务**：看板上 `hermes.exe kanban claim <task_id>`（完整路径 `C:\Users\<用户名>\Desktop\hermes-agent-main\.venv\Scripts\hermes.exe`）。
2. **放产物**：最终产物放 `tasks\<task_id>\`（不存在就创建），中间草稿可用自己的执行目录；**评论/总结里写共享路径**。
3. **可互相看**：允许阅读 `tasks\` 下任何目录；只写自己的，不删改他人的文件。
4. **公用材料**：跨任务复用素材放 `shared\`。
5. **回报**：卡上评论（完成了什么 / 产物路径 / 怎么验证 / 不确定的点）→ `kanban complete <id> --summary "..."`；需要人工接力 → `kanban block <id> "等待人工接力"`；回报前先实测产物存在（stat/ls）、绝对路径写全——防幽灵产物；**评论必须声明执行引擎**：『软件自身执行』（附命令行 + 软件自带日志路径）/『Hermes 工作进程代执行』——有可用通道时实质工作应经通道执行，不许把代执行写成软件执行。

## 已有产物

- `tasks\t_3d39b829-日志体检\report.md` — 日志体检 Top5（workBuddy）
- `tasks\t_f31bb65e\agent-setup.en.md` — 英文版自配置指令（最终版；t_0c99c119 空目录即幽灵事件现场）
- `shared\channel-capability.md` — 六通道能力矩阵（持续维护）；`shared\workbench-direction-20261009.md` — 工作台走向决策分析（六家软件智能体适配性评估）
- 优化轮（2026-10-09）：`tasks\t_f9499667\report-v7-audit.md`（v7 审计 Top5）、`tasks\t_f5bcedb6\report-race.md`（竞态根因+复现脚本）、`tasks\t_b032ba4f\report-logs-2.md`（日志二期）、`tasks\t_4dbf415a\report-en-check.md`（英译复核）、`tasks\t_eb3c081c\self-check.md`（trae-solo 首跑）、`tasks\t_3813dddd\report-v7-ux.md`（v7 界面评审，含 claude -p 对抗校对附A）
- 完善轮（2026-10-09）：`tasks\t_f50975e9\report-automation.md`（qoder：独立 CLI 可达全自动，差一次登录）、`tasks\t_e62d3d35\report-automation.md`（trae：chat 入口/无自动旗标）、`tasks\t_16fe3515\report-automation.md`（trae-solo：设置面免确认路径待实测）、`tasks\t_2a5e842d\report-automation.md`（workbuddy：CodeBuddy Code 内核 CLI）
- 上岗验收轮（2026-10-09 夜）：A 档四家真引擎 4/4 验收通过（`t_98265025` / `t_f33e2f41` / `t_6661f2b6` / `t_f946adc4`，卡评+附件+run 目录为凭据）
- 首轮真活（2026-10-09/10）：v7 Top5 修复四卡 → F1 `t_05c56440`@claude-code、F2 `t_0b40c2c9`@dsh、F3 `t_6bc4bb51`@qoder、F4 `t_5a69202d`@workbuddy；基准快照+diff+合并版在 `shared\fix-round-20261009\`（merge\ 已集成上 live，md5 `cebcfbee…`）
- 深夜续轮（2026-10-10）：**workbuddy 原生通道打通**（完整版 CodeBuddy Code 2.164.0 + 腾讯账号登录 + Hy4 preview 拉满：effort max / 960k 上下文）；**qoder/workbuddy 内置模型均可从流程图直接改**；总览面板引擎行上线；**qoder 默认=免费版 Qwen3.8-Flash，拉满（极高/xhigh + 上下文 1M）**
- **正式启用（2026-10-10）**：多智能体工作台正式启用。共享 Skill/MCP 库上线（`hub\`：claude-code 64 技能 + 4 MCP、qoder 82 技能 + 5 MCP、workbuddy 64 技能经 hermes-hub 市场 + 4 MCP ✓ Connected）；审美优化轮（5 个设计技能入库 + 工作台皮肤细节层 live 生效：阅读列 64rem / 海军蓝气泡 / 冷调编辑器 / 统一滚动条）
