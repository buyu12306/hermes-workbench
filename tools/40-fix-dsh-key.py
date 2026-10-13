# Repair the DeepSeek Harness key: replace the stored invalid key (tail c762)
# with Hermes's working key. Values are never printed.
import os
import sys
from pathlib import Path

REPO = Path(r'C:/Users/<用户名>/Desktop/hermes-agent-main')
sys.path.insert(0, str(REPO))
os.chdir(REPO)

from hermes_cli.profiles import _load_yaml_dict  # noqa: E402
from hermes_cli.config import load_config  # noqa: E402
from utils import atomic_yaml_write  # noqa: E402

home = Path(os.environ['USERPROFILE'])
creds_path = home / '.dsh' / '.credentials.yaml'

creds = _load_yaml_dict(creds_path)
if not isinstance(creds, dict):
    print('credentials unreadable'); sys.exit(1)

cfg = load_config() or {}
good_key = str((cfg.get('model') or {}).get('api_key') or '').strip()
print('hermes key len:', len(good_key))
if not good_key:
    print('no good key found'); sys.exit(1)


def walk(o, path=''):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk(v, f'{path}/{k}')
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, f'{path}[{i}]')
    else:
        yield path, o


hits = [(p, v) for p, v in walk(creds) if isinstance(v, str) and v.endswith('c762')]
print('invalid-key paths found:', [p for p, _ in hits])


def replace(o):
    n = 0
    if isinstance(o, dict):
        for k in list(o.keys()):
            v = o[k]
            if isinstance(v, str) and v.endswith('c762'):
                o[k] = good_key
                n += 1
            else:
                n += replace(v)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            if isinstance(v, str) and v.endswith('c762'):
                o[i] = good_key
                n += 1
            else:
                n += replace(v)
    return n


count = replace(creds)
print('replaced:', count)
if count:
    atomic_yaml_write(creds_path, creds, sort_keys=False)
    print('credentials updated')
else:
    print('nothing to replace')
