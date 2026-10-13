# -*- coding: utf-8 -*-
"""91-keepawake-diag2.py — correlation: agent.log writes vs daemon HOLD windows vs root sessions.

Answers: were the daemon's HOLD windows driven by REAL session turns, or by
ambient (non-task) writes into root agent.log?
"""
import collections
import datetime
import os
import pathlib
import re
import sqlite3
import time

HOME = pathlib.Path(os.environ.get('LOCALAPPDATA', r'C:\Users\<用户名>\AppData\Local')) / 'hermes'
now = time.time()

print('=== agent.log ===')
ap = HOME / 'logs' / 'agent.log'
st = ap.stat()
print('size_bytes', st.st_size, 'mtime_age_s', round(now - st.st_mtime, 1))
txt = ap.read_text(encoding='utf-8', errors='replace')
lines = txt.splitlines()
print('total_lines', len(lines))
print('--- last 6 lines ---')
for l in lines[-6:]:
    print(l[:220])

print('--- per-minute write counts 17:00-21:12 + first sample ---')
pat = re.compile(r'^(2026-10-12 (1[789]|2[01]):(\d\d))')
by_min = collections.Counter()
first = {}
for l in lines:
    m = pat.match(l)
    if m:
        by_min[m.group(1)] += 1
        first.setdefault(m.group(1), l[:200])
mins = sorted(by_min)
# print runs: only minutes with writes, plus gap markers
prev = None
for k in mins:
    print(k, 'writes=%d' % by_min[k], '|', first[k])

print()
print('=== root state.db: message activity 18:00-21:12 by minute/session ===')
con = sqlite3.connect('file:%s?mode=ro' % (HOME / 'state.db').as_posix(), uri=True, timeout=3)
con.row_factory = sqlite3.Row
try:
    rows = con.execute('SELECT session_id, role, timestamp FROM messages WHERE timestamp > ? ORDER BY timestamp',
                       (now - 3 * 3600 * 4,)).fetchall()
except Exception as e:
    rows = []
    print('ERR', e)
by2 = collections.Counter()
for r in rows:
    t = datetime.datetime.fromtimestamp(float(r['timestamp']))
    if t.day == 12:
        key = t.strftime('%H:%M')
        by2[(key, r['session_id'])] += 1
for (k, sid), c in sorted(by2.items()):
    print(k, c, sid[:40])

print()
print('=== daemon hold windows (from its log) vs activity ===')
kl = (HOME / 'logs' / 'keepawake.log').read_text(encoding='utf-8', errors='replace').splitlines()
for l in kl[-14:]:
    print(l)
