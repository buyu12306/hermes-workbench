# Add DISABLE_NON_ESSENTIAL_MODEL_CALLS=1 to the Claude Code settings env.
import io
import json
import os
from pathlib import Path

p = Path(os.environ['USERPROFILE']) / '.claude' / 'settings.json'
d = json.load(io.open(p, encoding='utf-8'))
env = d.setdefault('env', {})
env['DISABLE_NON_ESSENTIAL_MODEL_CALLS'] = '1'
io.open(p, 'w', encoding='utf-8').write(json.dumps(d, ensure_ascii=False, indent=2) + '\n')
print('env keys:', sorted(env.keys()))
