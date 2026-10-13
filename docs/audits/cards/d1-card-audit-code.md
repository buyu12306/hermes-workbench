【任务】对工作台核心自研代码做一次**只读**深度审计，产出问题清单与「复刻性」硬编码清单。

【范围（只读，不许修改任何文件）】
1. C:\Users\<用户名>\AppData\Local\hermes\desktop-plugins\workbench-graph\plugin.js （约60KB）
2. C:\Users\<用户名>\AppData\Local\hermes\desktop-plugins\workbench-overview\plugin.js
3. C:\Users\<用户名>\AppData\Local\hermes\desktop-plugins\workbench-field\plugin.js
4. C:\Users\<用户名>\AppData\Local\hermes\plugins\workbench-graph\dashboard\plugin_api.py （约40KB）

【产物】C:\Users\<用户名>\Desktop\工作区\Hermes工作台\tasks\<本卡ID>\report-audit-code.md
结构：
- A. Top 10 问题（按严重度排序）：每条 = 文件:行号 / 现象 / 根因 / 修复建议（具体到做法）/ 验证方法。覆盖维度：正确性、异常与边界、安全（后端 API 的输入校验/路径穿越/命令注入；前端 innerHTML/XSS）、资源（监听与定时器未清理、内存滞涨）、竞态。
- B. 硬编码清单：所有写死的本机路径/用户名/端口/软件安装位置（文件:行号 + 原值），供「复刻包参数化」用。
- C. 三条「必须保留的行为」：审计中发现的、看似可疑但实际有意为之的设计（防止复刻时误改）。

【硬性要求】
- 每个行号必须重新对照文件核实后再写（不许凭记忆；写前用工具读一次原文）。
- 只读：不改任何文件。报告完成后在卡上评论：执行引擎声明 + 报告绝对路径 + stat 证据。
- 时间盒 ~30 分钟；报告 ≤400 行。
