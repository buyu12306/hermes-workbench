# Probe available models on the configured custom provider. Never prints the API key.
import json
import os
import sys
import urllib.request
from pathlib import Path

REPO = Path(r'C:/Users/<用户名>/Desktop/hermes-agent-main')
sys.path.insert(0, str(REPO))
os.chdir(REPO)

import yaml  # noqa: E402

cfg_path = Path(os.environ['LOCALAPPDATA']) / 'hermes' / 'config.yaml'
cfg = yaml.safe_load(cfg_path.read_text(encoding='utf-8')) or {}
m = cfg.get('model') or {}
base = str(m.get('base_url') or '').rstrip('/')
key = str(m.get('api_key') or '')
print('base_url:', base)
print('default :', m.get('default'))
print('key len :', len(key))

req = urllib.request.Request(base + '/models', headers={'Authorization': 'Bearer ' + key})
try:
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    ids = sorted({str(x.get('id')) for x in (data.get('data') or []) if isinstance(x, dict)})
    print('models:', ', '.join(ids) if ids else '(none)')
except Exception as exc:  # noqa: BLE001
    print('probe failed:', type(exc).__name__, str(exc)[:200])
