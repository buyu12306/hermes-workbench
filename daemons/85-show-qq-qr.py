# -*- coding: utf-8 -*-
"""Extract the QQ connect URL from the onboarding log, render a QR PNG, show it on screen."""
import os
import pathlib
import re
import subprocess
import time

SCRATCH = pathlib.Path(r'C:/Users/<用户名>/AppData/Local/hermes/cache/scratch')
LOG = SCRATCH / 'qq_onboard.log'

url = None
for i in range(60):
    try:
        t = LOG.read_text(encoding='utf-8', errors='replace') if LOG.exists() else ''
    except Exception:
        t = ''
    m = re.search(r'(https://q\.qq\.com/qqbot/openclaw/connect\.html\?task_id=[^\s]+)', t)
    if m:
        url = m.group(1).strip()
        break
    time.sleep(1)

print('URL:', url or 'NO_URL')
if not url:
    raise SystemExit(1)

import qrcode  # noqa: E402

img = qrcode.make(url)
png = SCRATCH / 'qq_qr.png'
img.save(png)
print('PNG:', png, png.stat().st_size, 'bytes')

try:
    os.startfile(str(png))  # default photo viewer pops on the user's desktop
    print('viewer opened')
except Exception as e:
    print('viewer err', e)

try:
    subprocess.run(
        ['powershell', '-NoProfile', '-Command',
         'Set-Clipboard -Value ([Console]::In.ReadToEnd())'],
        input=url.encode('utf-8'), timeout=15, check=False)
    print('clipboard set')
except Exception as e:
    print('clipboard err', e)
