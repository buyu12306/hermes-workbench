# -*- coding: utf-8 -*-
"""Apply QQ bot credentials from qq_creds.json into %LOCALAPPDATA%/hermes/.env (idempotent)."""
import json
import pathlib

HOME = pathlib.Path(r'C:/Users/<用户名>/AppData/Local/hermes')
creds_p = HOME / 'cache' / 'scratch' / 'qq_creds.json'
env_p = HOME / '.env'

creds = json.loads(creds_p.read_text(encoding='utf-8'))
assert creds and creds.get('app_id') and creds.get('client_secret'), 'creds missing/incomplete'

lines = []
if env_p.exists():
    lines = env_p.read_text(encoding='utf-8', errors='replace').splitlines()


def upsert(k, v):
    global lines
    lines = [l for l in lines if not l.strip().startswith(k + '=')]
    lines.append('%s=%s' % (k, v))


upsert('QQ_APP_ID', creds['app_id'])
upsert('QQ_CLIENT_SECRET', creds['client_secret'])
openid = (creds.get('user_openid') or '').strip()
if openid:
    upsert('QQ_ALLOWED_USERS', openid)
    upsert('QQBOT_HOME_CHANNEL', openid)
upsert('QQ_ALLOW_ALL_USERS', 'false')

env_p.write_text('\n'.join(lines) + '\n', encoding='utf-8')
ks = [l.split('=', 1)[0] for l in lines if l.strip() and not l.strip().startswith('#') and '=' in l]
print('env keys now:', ks)
if openid:
    (HOME / 'cache' / 'scratch' / 'qq_openid.txt').write_text(openid, encoding='utf-8')
    print('openid tail:', openid[-8:])
