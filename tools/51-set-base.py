# Swap only the ANTHROPIC_BASE_URL in ~/.claude/settings.json (key never printed).
import io
import json
import os
import sys
from pathlib import Path

url = sys.argv[1]
p = Path(os.environ['USERPROFILE']) / '.claude' / 'settings.json'
d = json.load(io.open(p, encoding='utf-8'))
d.setdefault('env', {})['ANTHROPIC_BASE_URL'] = url
io.open(p, 'w', encoding='utf-8').write(json.dumps(d, ensure_ascii=False, indent=2) + '\n')
print('base_url set to:', url)


# Also ensure hasCompletedOnboarding=true in ~/.claude.json
q = Path(os.environ['USERPROFILE']) / '.claude.json'
if q.exists():
    j = json.load(io.open(q, encoding='utf-8'))
    if j.get('hasCompletedOnboarding') is not True:
        j['hasCompletedOnboarding'] = True
        io.open(q, 'w', encoding='utf-8').write(json.dumps(j, ensure_ascii=False, indent=2) + '\n')
        print('onboarding flag set: true')
    else:
        print('onboarding flag already true')
else:
    io.open(q, 'w', encoding='utf-8').write(json.dumps({'hasCompletedOnboarding': True}, indent=2) + '\n')
    print('claude.json created with onboarding flag')
