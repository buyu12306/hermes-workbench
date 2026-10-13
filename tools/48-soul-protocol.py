# SOUL v3: clearer "how you work" line + collaboration protocol (board-mediated,
# structured handoffs — patterns borrowed from production multi-agent systems).
import io
from pathlib import Path

H = Path('C:/Users/<用户名>/AppData/Local/hermes/profiles')
NAMES = ['claude-code', 'deepseek-harness', 'qoder', 'trae', 'trae-solo', 'workbuddy']

OLD_NOTE = ('干活交给软件自己的模型与账户（走软件自己的凭据与额度）：你只负责对接、核验与回报；'
            '不要用别的 API 替它完成工作。')
NEW_NOTE = ('干活的方式：把实际任务交给软件自己的无头命令/界面执行，用软件自己的凭据与额度计费；'
            '你负责自评分工、对接执行、核验结果、写清回报（你的调度与判断运行在 Hermes 上，这很正常）。')

PROTOCOL = ('协作协议：\n'
            '- 卡上评论即对话：审阅、提问、决策都写在任务卡评论里，与工作同处一地，便于追溯。\n'
            '- 结构化交接：完成总结必须包含——产物路径 / 验证方法 / 结论与不确定点；接手者能照着复现。\n'
            '- 缺什么就明说：缺证据、缺权限、需要人工接力时，评论里写「需要：…」；能做多少先做多少。\n'
            '- 不越权：只动自己任务的工作区；需要别人配合时在评论里点名并说清要什么。\n\n')

MARK = 'You are Hermes Agent, built by Nous Research.'

for n in NAMES:
    p = H / n / 'SOUL.md'
    t = io.open(p, encoding='utf-8').read()
    changed = False
    if OLD_NOTE in t:
        t = t.replace(OLD_NOTE, NEW_NOTE, 1)
        changed = True
    if '协作协议：' not in t:
        if MARK in t:
            t = t.replace(MARK, PROTOCOL + MARK, 1)
        else:
            t = t.rstrip() + '\n\n' + PROTOCOL
        changed = True
    if changed:
        io.open(p, 'w', encoding='utf-8').write(t)
        print(n, ':updated')
    else:
        print(n, ':no-change')
print('DONE')
