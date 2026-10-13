# -*- coding: utf-8 -*-
"""94-keepawake-watch.py — post-turn idle observation (v2).

Samples at T+8, T+20, T+35, T+55, T+80 minutes: keep-awake daemon log tail,
root agent.log recency, session/lease state, kanban state, app keep-awake
config, keepawake-power.json + live AC standby timeout, and NEW battery-report
state transitions (machine sleep entries). Appends to keepawake-watch.txt.
"""
import datetime
import os
import pathlib
import re
import sqlite3
import subprocess
import time

HOME = pathlib.Path(os.environ.get('LOCALAPPDATA', r'C:\Users\<用户名>\AppData\Local')) / 'hermes'
APPDATA = pathlib.Path(os.environ.get('APPDATA', r'C:\Users\<用户名>\AppData\Roaming'))
SCRATCH = HOME / 'cache' / 'scratch'
OUT = SCRATCH / 'keepawake-watch.txt'
BATT = SCRATCH / 'battreport.html'
START = time.time()


def batt_states():
    """Parse recent-usage rows from a fresh battery report."""
    try:
        subprocess.run(['powercfg', '/batteryreport', '/output', str(BATT)],
                       capture_output=True, timeout=60)
        html = BATT.read_text(encoding='utf-8', errors='replace')
        rows = []
        for m in re.finditer(r'(20\d\d-\d\d-\d\d \d\d:\d\d:\d\d)</td>\s*<td[^>]*>([^<]*)</td>\s*<td[^>]*>([^<]*)</td>', html):
            ts, src, state = m.group(1), m.group(2).strip(), m.group(3).strip()
            rows.append((ts, src, state))
        return rows[-60:]
    except Exception as e:
        return [('ERR', '', repr(e))]


def power_ac_sec():
    """Live AC standby timeout (STANDBYIDLE) seconds, or None."""
    try:
        r = subprocess.run(['powercfg', '/query', 'SCHEME_CURRENT', 'SUB_SLEEP', 'STANDBYIDLE'],
                           capture_output=True, timeout=30)
        out = r.stdout.decode('mbcs', errors='replace')
        vals = re.findall(r'0x([0-9a-fA-F]{1,8})', out)
        if len(vals) >= 2:
            return int(vals[-2], 16)
    except Exception:
        pass
    return None


def snap(tag):
    now = time.time()
    lines = []
    lines.append('=== %s (elapsed %.0f min) @ %s ===' % (
        tag, (now - START) / 60.0, datetime.datetime.now().strftime('%H:%M:%S')))
    kl = HOME / 'logs' / 'keepawake.log'
    if kl.exists():
        lines.append('keepawake.log tail: ' + ' || '.join(kl.read_text(encoding='utf-8', errors='replace').splitlines()[-6:]))
    pw = HOME / 'keepawake-power.json'
    lines.append('power json: %s | live standby-ac=%ss' % (
        pw.read_text(encoding='utf-8', errors='replace').replace('\n', ' ') if pw.exists() else 'missing',
        power_ac_sec()))
    al = HOME / 'logs' / 'agent.log'
    if al.exists():
        lines.append('root agent.log age=%.0fs' % (now - al.stat().st_mtime))
        tail = al.read_text(encoding='utf-8', errors='replace').splitlines()[-4:]
        lines.append('agent.log tail: ' + ' || '.join(t[:160] for t in tail))
    try:
        con = sqlite3.connect('file:%s?mode=ro' % (HOME / 'state.db').as_posix(), uri=True, timeout=5)
        n = con.execute('SELECT COUNT(*) FROM session_turn_leases WHERE expires_at > ?', (now,)).fetchone()[0]
        a = con.execute('SELECT MAX(timestamp) FROM messages').fetchone()[0]
        lines.append('root leases_active=%s msg_age=%.0fs' % (n, (now - float(a)) if a else -1))
        con.close()
    except Exception as e:
        lines.append('root db err %r' % e)
    try:
        con = sqlite3.connect('file:%s?mode=ro' % (HOME / 'kanban.db').as_posix(), uri=True, timeout=5)
        r = con.execute("SELECT COUNT(*) FROM tasks WHERE status IN ('running','claimed')").fetchone()
        lines.append('kanban running/claimed=%s' % (r[0] if r else '?'))
        con.close()
    except Exception as e:
        lines.append('kanban err %r' % e)
    lines.append('flag=%s' % (HOME / 'keep-awake.on').exists())
    aj = APPDATA / 'Hermes' / 'keep-awake.json'
    lines.append('app_json=%s' % (aj.read_text(encoding='utf-8', errors='replace').replace('\n', ' ') if aj.exists() else 'missing'))
    rows = batt_states()
    lines.append('recent machine state transitions (battery report, last 12):')
    for ts, src, state in rows[-12:]:
        lines.append('   %s | %s | %s' % (ts, state, src))
    with open(OUT, 'a', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n\n')


snap('T+8min')
time.sleep(720)
snap('T+20min')
time.sleep(900)
snap('T+35min')
time.sleep(1200)
snap('T+55min')
time.sleep(1500)
snap('T+80min')
print('watch done -> %s' % OUT)
