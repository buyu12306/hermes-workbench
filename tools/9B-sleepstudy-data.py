# -*- coding: utf-8 -*-
"""9B-sleepstudy-data.py — find the embedded JSON data in sleepstudy.html and print session reasons."""
import re
import pathlib

p = pathlib.Path(r'C:\Users\<用户名>\AppData\Local\hermes\cache\scratch\powerprobe\sleepstudy.html')
h = p.read_text(encoding='utf-8', errors='replace')

for key in ('EnterReason', 'EntryReason', 'ExitReason', 'ReasonDescription'):
    idxs = [m.start() for m in re.finditer(key, h)]
    print('key %r: %d occurrences' % (key, len(idxs)))
    for i in idxs[:3]:
        print('   ctx:', repr(h[max(0, i - 120):i + 260])[:520])

# look for the data blob markers
for key in ('window.data', 'var data', 'ModelData', '=\s*\{"', 'SessionId'):
    idxs = [m.start() for m in re.finditer(key, h)]
    print('marker %r: %d' % (key, len(idxs)))
    for i in idxs[:2]:
        print('   ctx:', repr(h[max(0, i - 100):i + 300])[:480])

# recent date strings
idxs = [m.start() for m in re.finditer(r'2026-10-12', h)]
print('2026-10-12 occurrences:', len(idxs))
for i in idxs[:5]:
    print('   ctx:', repr(h[max(0, i - 150):i + 250])[:500])
