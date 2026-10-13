【任务】**只读**审计工作台自研界面层的中文完整度，产出「英文残留」逐条清单（用户硬性要求中文界面，含角落小字）。

【范围（只读，不许修改）】
1. C:\Users\<用户名>\AppData\Local\hermes\desktop-plugins\workbench-graph\plugin.js
2. C:\Users\<用户名>\AppData\Local\hermes\desktop-plugins\workbench-overview\plugin.js
3. C:\Users\<用户名>\AppData\Local\hermes\desktop-plugins\workbench-field\plugin.js
4. C:\Users\<用户名>\AppData\Local\hermes\plugins\workbench-graph\dashboard\plugin_api.py（只挑用户可能看到的文案，如错误消息）
5. C:\Users\<用户名>\AppData\Local\hermes\workbench-graph\agent-setup.md（这页会被用户复制给各家软件）

【产物】C:\Users\<用户名>\Desktop\工作区\Hermes工作台\tasks\<本卡ID>\report-i18n.md
- 表A「应收录（英文残留）」：文件:行号 | 现文案 | 建议中文 | 出现位置（界面哪个角落/哪种状态）。
- 表B「保留英文（已确认）」：约定俗成应保持英文的（模型名如 Step-5-Preview、协议名 MCP/SSE、品牌名 Hermes、命令示例、路径、代码标识符）——单列说明，避免复刻者误改。
【判定标准】用户可见的按钮/标签/标题/提示/空状态/错误消息是英文 → 表A；是变量名/代码/日志内部文案 → 不入表。若某处已有中英混排但合理（如「⚙ 设置 / Settings」），说明取舍理由。
【硬性要求】行号逐一核实再写；只读；卡评：引擎声明 + 报告绝对路径 + stat 证据；时间盒 ~30 分钟；≤300 行。
