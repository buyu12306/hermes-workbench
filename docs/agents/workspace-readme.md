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
5. **回报**：卡上评论（完成了什么 / 产物路径 / 怎么验证 / 不确定的点）→ `kanban complete <id> --summary "..."`；需要人工接力 → `kanban block <id> "等待人工接力"`。

## 已有产物

- `tasks\t_3d39b829-日志体检\report.md` — 日志体检 Top5（workBuddy）
- `tasks\t_0c99c119-英文指令\` — 英文版自配置指令（重派中）
