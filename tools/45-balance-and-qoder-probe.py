# Probe: (1) DeepSeek balance via dsh's own credentials; (2) qoder ai-stats snapshots peek.
import io
import json
import os
import sys
import urllib.request
from pathlib import Path

REPO = Path(r'C:/Users/<用户名>/Desktop/hermes-agent-main')
sys.path.insert(0, str(REPO))

from hermes_cli.profiles import _load_yaml_dict  # noqa: E402

home = Path(os.environ['USERPROFILE'])

# --- 1) deepseek balance via dsh's own key file
try:
    creds = _load_yaml_dict(home / '.dsh' / '.credentials.yaml') or {}
    key = str(((creds.get('refs') or {}).get('DEEPSEEK_API_KEY')) or '')
    print('dsh key len:', len(key))
    req = urllib.request.Request(
        'https://api.deepseek.com/user/balance',
        headers={'Authorization': 'Bearer ' + key, 'Accept': 'application/json'})
    data = json.load(urllib.request.urlopen(req, timeout=10))
    print('balance ok:', data.get('is_available'))
    for i in (data.get('balance_infos') or []):
        print('  currency:', i.get('currency'), '| total:', i.get('total_balance'),
              '| granted:', i.get('granted_balance'), '| topped:', i.get('topped_up_balance'))
except Exception as e:
    print('balance ERR:', type(e).__name__, str(e)[:160])

# --- 2) qoder snapshots
snap = home / '.qoder-cli' / 'ai-stats' / 'snapshots'
files = sorted(snap.rglob('*')) if snap.exists() else []
files = [f for f in files if f.is_file()]
print('qoder snapshot files:', len(files))
for f in files[-3:]:
    print('---', f.relative_to(snap), f.stat().st_size)
    try:
        d = json.load(io.open(f, encoding='utf-8'))
        if isinstance(d, dict):
            print('    keys:', list(d.keys())[:16])
        elif isinstance(d, list) and d:
            print('    list[0] keys:', list(d[0].keys())[:16] if isinstance(d[0], dict) else type(d[0]).__name__)
    except Exception as e:
        print('    parse err:', str(e)[:80])

# --- 3) workbuddy quick check for usage/account
wb = home / '.workbuddy'
print('workbuddy subdirs:', [p.name for p in wb.iterdir()][:16] if wb.exists() else 'missing')
