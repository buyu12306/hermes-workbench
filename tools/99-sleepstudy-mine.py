# -*- coding: utf-8 -*-
"""99-sleepstudy-mine.py — extract recent sessions + reasons from the 11MB sleepstudy.html."""
import re
import pathlib

p = pathlib.Path(r'C:\Users\<用户名>\AppData\Local\hermes\cache\scratch\powerprobe\sleepstudy.html')
h = p.read_text(encoding='utf-8', errors='replace')
print('size', len(h))

# section headers
for m in re.finditer(r'<h([123])[^>]*>(.*?)</h\1>', h, re.S):
    t = re.sub(r'<[^>]+>', ' ', m.group(2))
    t = re.sub(r'\s+', ' ', t).strip()
    if t:
        print('H%s: %s' % (m.group(1), t[:150]))

# all table rows -> text, keep last N
rows = []
for m in re.finditer(r'<tr[^>]*>(.*?)</tr>', h, re.S):
    cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', m.group(1), re.S)
    txt = ' | '.join(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', c)).strip() for c in cells)
    if txt.strip():
        rows.append(txt)
print('total rows', len(rows))
print('=== last 120 rows ===')
for r in rows[-120:]:
    print(r[:300])
