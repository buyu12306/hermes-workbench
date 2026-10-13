# Direct-write bot ui_meta (title/groups/avatar) + display_name into profile.yaml,
# mirroring tui_gateway.methods_profiles._configure_ui_meta semantics:
#   - ui_meta is merged key-wise (top-level keys = plugin ids, replaced wholesale)
#   - _ui_meta_revisions[key] += 1 per touched key
#   - atomic write via the repo's own writer
import os
import sys
from pathlib import Path

REPO = Path(r'C:/Users/<用户名>/Desktop/hermes-agent-main')
sys.path.insert(0, str(REPO))
os.chdir(REPO)

from utils import atomic_yaml_write  # noqa: E402
from hermes_cli.profiles import write_profile_meta  # noqa: E402
from tui_gateway.methods_profiles import _read_profile_yaml  # noqa: E402

H = Path(os.environ['LOCALAPPDATA']) / 'hermes'

BOTS = [
    ('default',    '总管',   '#f2c14e', 'hexagon'),
    ('researcher', '研究员', '#6db3f2', 'circle'),
    ('builder',    '工程师', '#63c88b', 'squircle'),
    ('scribe',     '撰稿人', '#d98adf', 'cloud'),
]
GROUPS = ['工作群']

ok = True
for name, title, color, shape in BOTS:
    pdir = H if name == 'default' else H / 'profiles' / name
    try:
        write_profile_meta(pdir, display_name=title)
        existing = _read_profile_yaml(pdir) or {}
        ui = existing.get('ui_meta')
        ui = dict(ui) if isinstance(ui, dict) else {}
        prev = ui.get('hermes-bots')
        merged = dict(prev) if isinstance(prev, dict) else {}
        merged.update({'title': title, 'groups': GROUPS, 'color': color, 'shape': shape, 'custom': True})
        ui['hermes-bots'] = merged
        existing['ui_meta'] = ui
        revs = existing.get('_ui_meta_revisions')
        revs = dict(revs) if isinstance(revs, dict) else {}
        revs['hermes-bots'] = int(revs.get('hermes-bots') or 0) + 1
        existing['_ui_meta_revisions'] = revs
        atomic_yaml_write(pdir / 'profile.yaml', existing, sort_keys=False)
        print(f'{name}: written (rev {revs["hermes-bots"]}, title {title!r})')
    except Exception as exc:  # noqa: BLE001
        ok = False
        print(f'{name}: ERROR {type(exc).__name__}: {exc}')

print('ALL-OK' if ok else 'SOME-FAILED')
