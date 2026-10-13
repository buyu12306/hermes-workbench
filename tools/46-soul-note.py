# Append the "use the software's own model/account" line to the six bridge SOULs.
import io
from pathlib import Path

H = Path('C:/Users/<用户名>/AppData/Local/hermes/profiles')
NAMES = ['claude-code', 'deepseek-harness', 'qoder', 'trae', 'trae-solo', 'workbuddy']
MARK = 'You are Hermes Agent, built by Nous Research.'
NOTE = ('干活交给软件自己的模型与账户（走软件自己的凭据与额度）：你只负责对接、核验与回报；'
        '不要用别的 API 替它完成工作。\n\n')

for n in NAMES:
    p = H / n / 'SOUL.md'
    text = io.open(p, encoding='utf-8').read()
    if '软件自己的模型与账户' in text:
        print(n, ': already noted')
        continue
    if MARK in text:
        text = text.replace(MARK, NOTE + MARK, 1)
    else:
        text = text.rstrip() + '\n\n' + NOTE
    io.open(p, 'w', encoding='utf-8').write(text)
    print(n, ': note added')
print('DONE')
