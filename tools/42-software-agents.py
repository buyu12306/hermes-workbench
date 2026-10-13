# Software-agent roster: display names + ui_meta + model pin for the six bridges.
import os
import sys
from pathlib import Path

REPO = Path(r'C:/Users/<用户名>/Desktop/hermes-agent-main')
sys.path.insert(0, str(REPO))
os.chdir(REPO)

from hermes_cli.profiles import write_profile_meta, _load_yaml_dict  # noqa: E402
from utils import atomic_yaml_write  # noqa: E402

H = Path(os.environ['LOCALAPPDATA']) / 'hermes'

BOTS = [
    ('claude-code',      'Claude Code',      '#d97757', 'hexagon'),
    ('deepseek-harness', 'DeepSeek Harness', '#6db3f2', 'circle'),
    ('qoder',            'Qoder',            '#7d8cff', 'squircle'),
    ('trae',             'Trae',             '#63c88b', 'pill'),
    ('trae-solo',        'TRAE SOLO',        '#b58dd8', 'cloud'),
    ('workbuddy',        'WorkBuddy',        '#ef8f4a', 'triangle'),
]
GROUPS = ['工作群']
MODEL = 'deepseek-v4-pro'

for name, title, color, shape in BOTS:
    pdir = H / 'profiles' / name
    # 1) display name
    write_profile_meta(pdir, display_name=title)
    # 2) ui_meta (merge + revision bump), same shape _configure_ui_meta writes
    ppath = pdir / 'profile.yaml'
    meta = _load_yaml_dict(ppath) or {}
    ui = meta.get('ui_meta')
    ui = dict(ui) if isinstance(ui, dict) else {}
    prev = ui.get('hermes-bots')
    merged = dict(prev) if isinstance(prev, dict) else {}
    merged.update({'title': title, 'groups': GROUPS, 'color': color, 'shape': shape, 'custom': True})
    ui['hermes-bots'] = merged
    meta['ui_meta'] = ui
    revs = meta.get('_ui_meta_revisions')
    revs = dict(revs) if isinstance(revs, dict) else {}
    revs['hermes-bots'] = int(revs.get('hermes-bots') or 0) + 1
    meta['_ui_meta_revisions'] = revs
    atomic_yaml_write(ppath, meta, sort_keys=False)
    # 3) model pin (high-intelligence for orchestration turns)
    cpath = pdir / 'config.yaml'
    cfg = _load_yaml_dict(cpath) or {}
    model = cfg.get('model')
    model = dict(model) if isinstance(model, dict) else {}
    model['default'] = MODEL
    cfg['model'] = model
    atomic_yaml_write(cpath, cfg, sort_keys=False)
    print(f'{name}: ui_meta rev {revs["hermes-bots"]}, model -> {MODEL}')

print('DONE')
