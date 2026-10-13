# -*- coding: utf-8 -*-
"""91c-reconcile-scan.py — who writes root agent.log when 'idle'? Full timeline 18:00-21:15."""
import collections
import os
import pathlib
import re
import time

HOME = pathlib.Path(os.environ.get('LOCALAPPDATA', r'C:\Users\<用户名>\AppData\Local')) / 'hermes'
ap = HOME / 'logs' / 'agent.log'
lines = ap.read_text(encoding='utf-8', errors='replace').splitlines()

ts_re = re.compile(r'^(\d{4}-\d{2}-\d{2} (\d{2}):(\d{2}):(\d{2})[,.]\d+)')
today = '2026-10-12'

# ---- 1) reconcile timeline (whole file) ----
rec = [l for l in lines if 'run_profile_reconcile' in l]
print('reconcile lines total:', len(rec))
if rec:
    print('first:', rec[0][:90])
    print('last :', rec[-1][:90])
    stamps = []
    for l in rec:
        m = ts_re.match(l)
        if m:
            stamps.append(m.group(1))
    # gaps > 150s
    import datetime as dt
    def pt(s):
        return dt.datetime.strptime(s.split(',')[0], '%Y-%m-%d %H:%M:%S')
    prev = None
    gaps = []
    for s in stamps:
        t = pt(s)
        if prev and (t - prev).total_seconds() > 150:
            gaps.append((prev.strftime('%m-%d %H:%M:%S'), s, int((t - prev).total_seconds())))
        prev = t
    print('gaps>150s between reconcile lines (last 15):')
    for g in gaps[-15:]:
        print('  gap', g)

# ---- 2) per-minute counts with logger name, 18:00-21:12 ----
print()
print('=== per-minute writes 18:00-21:12 (count | first line) ===')
by_min = collections.Counter()
first = {}
for l in lines:
    m = ts_re.match(l)
    if not m:
        continue
    if m.group(2) >= '18' and today in l[:12]:
        key = l[11:16]
        by_min[key] += 1
        first.setdefault(key, l[:150])
    elif today in l[:12] and m.group(2) in ('19', '20', '21'):
        key = l[11:16]
        by_min[key] += 1
        first.setdefault(key, l[:150])
for k in sorted(by_min):
    print(k, by_min[k], '|', first[k])

# ---- 3) every line 18:44-18:52 and 20:28-21:06 (windows around daemon flips) ----
for win, a, b in (('18:44-18:52', '18:44', '18:52'), ('20:28-21:06', '20:28', '21:06')):
    print()
    print('=== ALL agent.log lines %s ===' % win)
    for l in lines:
        m = ts_re.match(l)
        if m and today in l[:12] and a <= l[11:16] <= b:
            print(l[:150])
