# Declare `providers.custom` directly in each profile's config.yaml (no late-bound helpers).
import os
import sys
from pathlib import Path

REPO = Path(r'C:/Users/<用户名>/Desktop/hermes-agent-main')
sys.path.insert(0, str(REPO))
os.chdir(REPO)

from tui_gateway.methods_profiles import _read_profile_yaml  # noqa: F401  (warms the import chain)
from utils import atomic_yaml_write  # noqa: E402
import yaml  # noqa: E402

print('yaml ok:', yaml.__version__)

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
    cfg = yaml.safe_load(cfg_path.read_text(encoding='utf-8')) or {}
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
