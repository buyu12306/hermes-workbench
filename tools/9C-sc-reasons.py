# -*- coding: utf-8 -*-
"""9C-sc-reasons.py — extract session enter/exit reasons for 10-11/10-12 from sleepstudy.html."""
import re
import pathlib

p = pathlib.Path(r'C:\Users\<用户名>\AppData\Local\hermes\cache\scratch\powerprobe\sleepstudy.html')
h = p.read_text(encoding='utf-8', errors='replace')

pat = re.compile(
    r'"SessionId":(\d+),"ActivityLevel":(\d+),"EnterReason":"([^"]*)","ExitReason":"([^"]*)",'
    r'"EntryTimestamp":"[^"]*","EntryTimestampLocal":"([^"]*)","ExitTimestamp":"[^"]*","ExitTimestampLocal":"([^"]*)",'
    r'"Duration":(\d+)'
)
rows = pat.findall(h)
print('sessions parsed:', len(rows))
print()
for sid, lvl, er, xr, etl, xtl, dur in rows:
    if '2026-10-11' in etl or '2026-10-12' in etl:
        d = int(dur) / 1e6
        print('sid=%-3s lvl=%s  %s -> %s  dur=%8.1fs  enter=%r  exit=%r'
              % (sid, lvl, etl[11:19], xtl[11:19], d, er, xr))
