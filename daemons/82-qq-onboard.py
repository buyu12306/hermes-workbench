# -*- coding: utf-8 -*-
"""Standalone QQ Bot scan-to-configure driver.

Runs the same qr_register() flow the gateway setup wizard uses:
creates a bind task on q.qq.com, prints the connect URL (for QR), polls until
the phone QQ scans + confirms, then saves the returned credentials to
<scratch>/qq_creds.json and prints QQ_CREDS_JSON.
"""
import json
import pathlib
import sys

CHECKOUT = r'C:/Users/<用户名>/Desktop/hermes-agent-main'
SCRATCH = pathlib.Path(r'C:/Users/<用户名>/AppData/Local/hermes/cache/scratch')
sys.path.insert(0, CHECKOUT)


def main():
    from gateway.platforms.qqbot import qr_register
    print('qr_register starting (timeout 540s)...', flush=True)
    creds = qr_register(timeout_seconds=540)
    payload = creds or None
    (SCRATCH / 'qq_creds.json').write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding='utf-8')
    print('QQ_CREDS_JSON ' + json.dumps(payload, ensure_ascii=False), flush=True)
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
