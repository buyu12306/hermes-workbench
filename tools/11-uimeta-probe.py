# Probe: replicate _configure_ui_meta step by step to surface the swallowed exception.
import os
import sys
from pathlib import Path

REPO = Path(r'C:/Users/<用户名>/Desktop/hermes-agent-main')
sys.path.insert(0, str(REPO))
os.chdir(REPO)

H = Path(os.environ['LOCALAPPDATA']) / 'hermes'
import json  # noqa: E402

from tui_gateway.methods_profiles import (  # noqa: E402
    _profile_ui_meta_lock, _read_profile_yaml, _clean_revisions,
)
print('lock:', type(_profile_ui_meta_lock).__name__)

pdir = H / 'profiles' / 'researcher'
existing = _read_profile_yaml(pdir)
print('read type:', type(existing).__name__, 'keys:', list(existing.keys()) if isinstance(existing, dict) else 'N/A')

incoming = {'hermes-bots': {'title': '研究员', 'groups': ['工作群'], 'color': '#6db3f2', 'shape': 'circle', 'custom': True}}
print('json len:', len(json.dumps(incoming)))

current = existing.get('ui_meta')
current = current if isinstance(current, dict) else {}
for key, value in incoming.items():
    current[key] = value
existing['ui_meta'] = current
raw = existing.get('_ui_meta_revisions')
revisions = _clean_revisions(raw if isinstance(raw, dict) else {})
for key in incoming:
    revisions[key] = revisions.get(key, 0) + 1
existing['_ui_meta_revisions'] = revisions

from utils import atomic_yaml_write  # noqa: E402
atomic_yaml_write(pdir / 'profile.yaml', existing, sort_keys=False)  # no try/except: let it blow up loudly
print('WRITE-OK')
print('final keys:', list(existing.keys()))
