# -*- coding: utf-8 -*-
"""91-keepawake-diag.py — per-signal snapshot of the keep-awake daemon's busy detection.

Run: .venv/Scripts/python.exe .build/workbench/91-keepawake-diag.py
Prints one JSON blob; run twice a few minutes apart to spot periodic writers.
"""
import datetime
import json
import os
import pathlib
import sqlite3
import time

HOME = pathlib.Path(os.environ.get('LOCALAPPDATA', r'C:\Users\<用户名>\AppData\Local')) / 'hermes'
APPDATA_ROAM = pathlib.Path(os.environ.get('APPDATA', r'C:\Users\<用户名>\AppData\Roaming'))
now = time.time()

out = {'ts': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'now': now}


def db_ro(p):
    return sqlite3.connect('file:%s?mode=ro' % pathlib.PurePath(p).as_posix(), uri=True, timeout=3.0)


def try_(fn, default=None):
    try:
        return fn()
    except Exception as e:
        return {'ERR': repr(e)}


# ---- flag file + app keep-awake.json ----
out['flag_keep_awake_on'] = (HOME / 'keep-awake.on').exists()

def app_conf():
    p = APPDATA_ROAM / 'Hermes' / 'keep-awake.json'
    if not p.exists():
        return {'exists': False}
    return {'exists': True, 'age_s': round(now - p.stat().st_mtime, 1),
            'content': p.read_text(encoding='utf-8', errors='replace')}
out['app_keep_awake_json'] = try_(app_conf)

# ---- root state.db ----
def root_db():
    res = {}
    con = db_ro(HOME / 'state.db')
    try:
        con.row_factory = sqlite3.Row
        rows = con.execute('SELECT * FROM session_turn_leases').fetchall()
        res['leases_count'] = len(rows)
        res['leases'] = []
        for r in rows[:30]:
            d = dict(r)
            if 'expires_at' in d:
                try:
                    d['expires_in_s'] = round(float(d['expires_at']) - now, 1)
                except Exception:
                    pass
            res['leases'].append(d)
        r = con.execute('SELECT MAX(timestamp) FROM messages').fetchone()
        res['messages_max_age_s'] = round(now - float(r[0]), 1) if r and r[0] else None
        res['delegations_by_state'] = [
            dict(x) for x in con.execute(
                'SELECT state, COUNT(*) c FROM async_delegations GROUP BY state').fetchall()]
        # newest delegations detail
        res['delegations_newest'] = []
        for x in con.execute('SELECT * FROM async_delegations ORDER BY rowid DESC LIMIT 3').fetchall():
            d = dict(x)
            for k, v in list(d.items()):
                if isinstance(v, str) and len(v) > 200:
                    d[k] = v[:200] + '...(len %d)' % len(v)
            for k in ('event_json', 'task_json', 'result_json'):
                d.pop(k, None)
            res['delegations_newest'].append(d)
    finally:
        con.close()
    return res
out['root_state_db'] = try_(root_db)

# ---- per-profile state.db ----
def profile_dbs():
    prof = {}
    for sp in sorted((HOME / 'profiles').glob('*/state.db')):
        name = sp.parent.name
        if name.startswith('.'):
            continue
        d = {}

        def one():
            con = db_ro(sp)
            try:
                r = con.execute('SELECT COUNT(*) FROM session_turn_leases WHERE expires_at > ?', (now,)).fetchone()
                d['leases_active'] = r[0] if r else None
                r = con.execute('SELECT MAX(timestamp) FROM messages').fetchone()
                d['messages_max_age_s'] = round(now - float(r[0]), 1) if r and r[0] else None
                try:
                    rows = con.execute(
                        'SELECT session_id, role, timestamp, substr(content,1,100) FROM messages '
                        'ORDER BY timestamp DESC LIMIT 3').fetchall()
                    d['last_msgs'] = [list(x) for x in rows]
                except Exception as e2:
                    d['last_msgs_err'] = repr(e2)
                try:
                    rows = con.execute(
                        'SELECT COUNT(*) FROM async_delegations WHERE state NOT IN '
                        "('completed','failed','cancelled','done','error')").fetchone()
                    d['delegations_active_ish'] = rows[0] if rows else None
                except Exception as e3:
                    d['delegations_err'] = repr(e3)
            finally:
                con.close()
        d['probe'] = try_(one)
        prof[name] = d
    return prof
out['profiles'] = try_(profile_dbs)

# ---- kanban db ----
def kanban():
    kb = {}
    con = db_ro(HOME / 'kanban.db')
    try:
        kb['size'] = (HOME / 'kanban.db').stat().st_size
        rows = con.execute('SELECT status, COUNT(*) c FROM tasks GROUP BY status').fetchall()
        kb['by_status'] = {r[0]: r[1] for r in rows}
        try:
            rows = con.execute(
                "SELECT id, status, updated_at, substr(title,1,80) FROM tasks "
                "WHERE status IN ('running','claimed','todo','ready') ORDER BY updated_at DESC LIMIT 20").fetchall()
            kb['active_cards'] = [list(r) for r in rows]
        except Exception as e:
            kb['active_cards_err'] = repr(e)
    finally:
        con.close()
    return kb
out['kanban_db'] = try_(kanban)

# ---- file ages: hermes\logs top-newest, kanban logs, profile logs ----
def file_ages():
    res = {}
    logs = HOME / 'logs'
    if logs.exists():
        items = sorted(logs.glob('*'), key=lambda p: p.stat().st_mtime, reverse=True)[:12]
        res['hermes_logs_newest'] = [[p.name, round(now - p.stat().st_mtime, 1)] for p in items]
    kl = HOME / 'kanban' / 'logs'
    if kl.exists():
        items = sorted(kl.glob('*.log'), key=lambda p: p.stat().st_mtime, reverse=True)[:8]
        res['kanban_logs_newest'] = [[p.name, round(now - p.stat().st_mtime, 1)] for p in items]
    pl = []
    for plog_dir in sorted((HOME / 'profiles').glob('*/logs')):
        for p in plog_dir.glob('*'):
            try:
                pl.append(['%s/%s' % (plog_dir.parent.name, p.name), round(now - p.stat().st_mtime, 1)])
            except Exception:
                pass
    pl.sort(key=lambda x: x[1])
    res['profile_logs_newest'] = pl[:14]
    return res
out['file_ages'] = try_(file_ages)

# ---- tails of the 2 newest profile log files (identify periodic writer) ----
def profile_log_tails():
    res = []
    files = []
    for plog_dir in sorted((HOME / 'profiles').glob('*/logs')):
        for p in plog_dir.glob('*'):
            try:
                files.append(p)
            except Exception:
                pass
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    for p in files[:2]:
        try:
            tail = p.read_text(encoding='utf-8', errors='replace').splitlines()[-6:]
        except Exception as e:
            tail = [repr(e)]
        res.append({'file': str(p), 'tail': tail})
    return res
out['profile_log_tails'] = try_(profile_log_tails)

# ---- root agent.log tail (who writes when apparently idle) ----
def agent_tail():
    p = HOME / 'logs' / 'agent.log'
    if not p.exists():
        return None
    try:
        return p.read_text(encoding='utf-8', errors='replace').splitlines()[-8:]
    except Exception as e:
        return [repr(e)]
out['agent_log_tail'] = try_(agent_tail)

print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
