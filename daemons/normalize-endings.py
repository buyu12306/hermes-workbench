# -*- coding: utf-8 -*-
"""Normalize the workbench daemon scripts to CRLF (cmd.exe cannot parse LF-only .cmd)."""
import os

files = [
    r'C:\Users\<用户名>\Desktop\hermes-agent-main\.build\workbench\90-keepawake.cmd',
    r'C:\Users\<用户名>\Desktop\hermes-agent-main\.build\workbench\73-wb-quota.py',
    r'C:\Users\<用户名>\Desktop\hermes-agent-main\.build\workbench\80-task-keepawake.py',
    r'C:\Users\<用户名>\Desktop\hermes-agent-main\.build\workbench\87-watch-cards.py',
    r'C:\Users\<用户名>\Desktop\hermes-agent-main\.build\workbench\88-watch-shutdown.py',
    r'C:\Users\<用户名>\Desktop\hermes-agent-main\.build\workbench\89-cancel-countdown.py',
    r'C:\Users\<用户名>\Desktop\hermes-agent-main\.build\workbench\83-gateway-relaunch.ps1',
    r'C:\Users\<用户名>\Desktop\hermes-agent-main\.build\workbench\81-keepawake-autostart.vbs',
    r'C:\Users\<用户名>\AppData\Local\hermes\codebuddy-gateway\supervisor.ps1',
]
for p in files:
    with open(p, 'rb') as fh:
        b = fh.read()
    orig = b
    b = b.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
    if b != orig:
        with open(p, 'wb') as fh:
            fh.write(b)
        print('CRLF-normalized:', os.path.basename(p))
    else:
        print('CRLF-ok:', os.path.basename(p))
