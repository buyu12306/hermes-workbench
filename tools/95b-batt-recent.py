# -*- coding: utf-8 -*-
"""95b-batt-recent.py — extract Connected standby / Active transitions from battery report (10-11 onward)."""
import re
import pathlib
import datetime

p = pathlib.Path(r'C:\Users\<用户名>\AppData\Local\hermes\cache\scratch\battreport.html')
h = p.read_text(encoding='utf-8', errors='replace')

rows = []
cur_date = ''
for m in re.finditer(
        r'<td class="dateTime"><span class="date">([^<]*)</span><span class="time">([^<]*)</span></td>\s*'
        r'<td class="state">\s*([A-Za-z ]+?)\s*</td>', h):
    d = m.group(1).strip()
    t = m.group(2).strip()
    st = m.group(3).strip()
    if d:
        cur_date = d
    rows.append((cur_date, t, st))

print('total transitions in report:', len(rows))
print()

def ts(r):
    try:
        return datetime.datetime.strptime(r[0] + ' ' + r[1], '%Y-%m-%d %H:%M:%S')
    except Exception:
        return None

sel = [r for r in rows if r[0] in ('2026-10-11', '2026-10-12')]
print('transitions 10-11/10-12:', len(sel))
for r in sel:
    print('%s %s  %s' % (r[0], r[1], r[2]))

print()
print('=== standby sessions (in->out) with durations ===')
prev = None
for r in sel:
    t = ts(r)
    if t is None:
        continue
    if r[2].lower().startswith('connected standby'):
        if prev and prev[1].lower().startswith('active'):
            pass
        prev = (t, r[2])
        ins = t
        print('ENTER standby at', t)
    elif r[2].lower().startswith('active'):
        if prev and prev[1].lower().startswith('connected standby'):
            dur = (t - prev[0]).total_seconds()
            print('   exit at %s  (duration %.0f min)' % (t, dur / 60.0))
        prev = (t, r[2])
