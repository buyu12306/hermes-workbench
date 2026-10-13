# Declare `providers.custom` in each profile's config.yaml so model switching
# validates through the official path (resolve_user_provider finds the endpoint).
# Copies base_url/api_key from the profile's own model block; never prints the key.
import os
import sys
from pathlib import Path

REPO = Path(r'C:/Users/<用户名>/Desktop/hermes-agent-main')
sys.path.insert(0, str(REPO))
os.chdir(REPO)

from tui_gateway.methods_profiles import _hermes_home_scope  # noqa: E402

H = Path(os.environ['LOCALAPPDATA']) / 'hermes'
HOMES = [
    ('default', H),
    ('researcher', H / 'profiles' / 'researcher'),
    ('builder', H / 'profiles' / 'builder'),
    ('scribe', H / 'profiles' / 'scribe'),
]

for name, home in HOMES:
    try:
        with _hermes_home_scope(home):
            from hermes_cli.config import load_config, save_config
            cfg = load_config() or {}
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
            save_config(cfg)
            print(f'{name}: providers.custom written (base_url set, key {"yes" if key else "no"}, models 2)')
    except Exception as exc:  # noqa: BLE001
        print(f'{name}: ERROR {type(exc).__name__}: {exc}')

print('DONE')
