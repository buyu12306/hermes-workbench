# Set bot display names + Bot-Mode ui_meta (title/groups/avatar) for the workbench team.
# Runs with the repo venv python; uses the SAME code paths the gateway RPC uses.
import os
import sys
from pathlib import Path

REPO = Path(r'C:/Users/<用户名>/Desktop/hermes-agent-main')
sys.path.insert(0, str(REPO))
os.chdir(REPO)

from hermes_cli.profiles import write_profile_meta  # noqa: E402
from tui_gateway.methods_profiles import _configure_ui_meta, _read_profile_yaml  # noqa: E402

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
        ui = existing.get('ui_meta') if isinstance(existing.get('ui_meta'), dict) else {}
        prev = ui.get('hermes-bots') if isinstance(ui.get('hermes-bots'), dict) else {}
        merged = dict(prev)
        merged.update({'title': title, 'groups': GROUPS, 'color': color, 'shape': shape, 'custom': True})
        applied = {}
        _configure_ui_meta(pdir, {'name': name, 'ui_meta': {'hermes-bots': merged}}, applied)
        state = 'OK' if applied.get('ui_meta') else 'FAILED'
        if not applied.get('ui_meta'):
            ok = False
        print(f'{name}: display_name set, ui_meta {state} rev={applied.get("ui_meta_revisions")}')
    except Exception as exc:  # noqa: BLE001
        ok = False
        print(f'{name}: ERROR {type(exc).__name__}: {exc}')

print('ALL-OK' if ok else 'SOME-FAILED')
