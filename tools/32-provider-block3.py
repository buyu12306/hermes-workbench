# Declare `providers.custom` in each profile's config.yaml — repo helpers only
# (direct `import yaml` does not resolve in this interpreter; repo loaders do).
import os
import sys
from pathlib import Path

REPO = Path(r'C:/Users/<用户名>/Desktop/hermes-agent-main')
sys.path.insert(0, str(REPO))
os.chdir(REPO)

from hermes_cli.profiles import _load_yaml_dict  # noqa: E402
from utils import atomic_yaml_write  # noqa: E402

H = Path(os.environ['LOCALAPPDATA']) / 'hermes'
HOMES = [
    ('default', H),
    ('researcher', H / 'profiles' / 'researcher'),
    ('builder', H / 'profiles' / 'builder'),
    ('scribe', H / 'profiles' / 'scribe'),
]

for name, home in HOMES:
    cfg_path = home / 'config.yaml'
    if not cfg_path.is_file():
        print(f'{name}: no config.yaml — skip')
        continue
    cfg = _load_yaml_dict(cfg_path) or {}
    model = cfg.get('model') or {}
    base = str(model.get('base_url') or '').strip()
    key = str(model.get('api_key') or '').strip()
    if not base:
        print(f'{name}: no model.base_url — skip')
        continue
    provs = cfg.get('providers')
    provs = dict(provs) if isinstance(provs, dict) else {}
    entry = dict(provs.get('custom')) if isinstance(provs.get('custom'), dict) else {}
    entry['base_url'] = base
    if key:
        entry['api_key'] = key
    entry['models'] = ['deepseek-v4-pro', 'deepseek-flash']
    provs['custom'] = entry
    cfg['providers'] = provs
    atomic_yaml_write(cfg_path, cfg, sort_keys=False)
    print(f'{name}: providers.custom written (endpoint set, key {"yes" if key else "no"})')

print('DONE')
