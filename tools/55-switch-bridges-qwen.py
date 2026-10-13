# Switch the six bridge profiles' Hermes-side model to the user's Qwen account
# (qwen3.8-flash via maas.qianwenaiapi.com OpenAI-compatible endpoint).
# The Qwen key is read from ~/.claude/settings.json (never printed).
import io
import json
import os
import sys
from pathlib import Path

REPO = Path(r'C:/Users/<用户名>/Desktop/hermes-agent-main')
sys.path.insert(0, str(REPO))
os.chdir(REPO)

from hermes_cli.profiles import _load_yaml_dict  # noqa: E402
from utils import atomic_yaml_write  # noqa: E402

home = Path(os.environ['USERPROFILE'])
cred = json.load(io.open(home / '.claude' / 'settings.json', encoding='utf-8'))
key = str((cred.get('env') or {}).get('ANTHROPIC_AUTH_TOKEN') or '').strip()
if not key:
    print('no qwen key found'); sys.exit(1)
print('qwen key len:', len(key))

BASE = 'https://maas.qianwenaiapi.com/compatible-mode/v1'
MODEL = 'qwen3.8-flash'
H = Path(os.environ['LOCALAPPDATA']) / 'hermes' / 'profiles'
NAMES = ['claude-code', 'deepseek-harness', 'qoder', 'trae', 'trae-solo', 'workbuddy']

for n in NAMES:
    cfg_path = H / n / 'config.yaml'
    cfg = _load_yaml_dict(cfg_path) or {}
    model = dict(cfg.get('model') or {})
    model.update({
        'provider': 'custom',
        'base_url': BASE,
        'default': MODEL,
        'api_key': key,
    })
    cfg['model'] = model
    providers = dict(cfg.get('providers') or {})
    providers['custom'] = {
        'base_url': BASE,
        'api_key': key,
        'models': [MODEL],
    }
    cfg['providers'] = providers
    atomic_yaml_write(cfg_path, cfg, sort_keys=False)
    print(n, '->', MODEL, '@ qianwen')

print('DONE')
