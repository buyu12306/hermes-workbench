# Probe available models on the configured provider via the repo's own config loader.
# Never prints the API key.
import json
import os
import sys
import urllib.request
from pathlib import Path

REPO = Path(r'C:/Users/<用户名>/Desktop/hermes-agent-main')
sys.path.insert(0, str(REPO))
os.chdir(REPO)

from hermes_cli.config import load_config  # noqa: E402

cfg = load_config() or {}
m = cfg.get('model') or {}
base = str(m.get('base_url') or '').rstrip('/')
key = str(m.get('api_key') or '')
print('base_url:', base)
print('default :', m.get('default'))
print('key len :', len(key))

req = urllib.request.Request(base + '/models', headers={'Authorization': 'Bearer ' + key})
try:
    with urllib.request.urlopen(req, timeout=25) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    ids = sorted({str(x.get('id')) for x in (data.get('data') or []) if isinstance(x, dict)})
    print('models:', ', '.join(ids) if ids else '(none)')
except Exception as exc:  # noqa: BLE001
    print('probe failed:', type(exc).__name__, str(exc)[:240])
