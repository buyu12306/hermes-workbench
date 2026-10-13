【任务】**只读**审计工作台的后台守护脚本与服务监督层，产出风险清单 + 「复刻包脚本取舍」建议。

【范围（只读，不许修改）】
C:\Users\<用户名>\Desktop\hermes-agent-main\.build\workbench\ 下：
- 80-task-keepawake.py（防睡眠守护 v3）
- 81-keepawake-autostart.vbs、90-keepawake.cmd（启停控制台）
- 94-keepawake-watch.py（休眠观察）
- 73-wb-quota.py（限免额度守护）、74-wb-fallback-setup.py（fallback 链配置）
- 87-watch-cards.py、88-watch-shutdown.py、89-cancel-countdown.py（看板/关机守护）
- 83-gateway-relaunch.ps1（网关重启）
C:\Users\<用户名>\AppData\Local\hermes\codebuddy-gateway\supervisor.ps1（本地网关监督，若存在）
运行佐证可只读查看：%LOCALAPPDATA%\hermes\logs\keepawake.log

【产物】C:\Users\<用户名>\Desktop\工作区\Hermes工作台\tasks\<本卡ID>\report-daemons.md
- 每个脚本一节：职责 / 关键风险 / 边界条件审查（重复实例、休眠恢复、旗标竞态、进程匹配误杀、日志无限增长、时钟回拨/跨天）/ 具体修复建议（做法级）。
- 末尾「复刻包建议」一节：① 哪些脚本是「必需组件」、哪些是「一次性开发工具」（列出判断依据）；② 每个必需脚本里需要参数化的硬编码值（文件:行号 + 原值）。
【硬性要求】行号逐一核实再写；只读；卡评：引擎声明 + 报告绝对路径 + stat 证据；时间盒 ~30 分钟；≤400 行。
