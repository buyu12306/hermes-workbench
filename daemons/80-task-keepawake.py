# -*- coding: utf-8 -*-
"""80-task-keepawake.py — Task-aware keep-awake daemon (Hermes workbench). v3

Holds the machine awake while there is in-flight work, and releases it when idle
so the normal idle sleep (5 min on AC here) proceeds.

Signals that count as "busy":
  - %LOCALAPPDATA%\\hermes\\keep-awake.on flag file exists          (manual hold)
  - root state.db: session_turn_leases expires_at > now             (turn in flight)
  - root state.db: messages max(timestamp) within RECENT_WINDOW     (session activity)
  - root state.db: async_delegations in an active state             (subagents)
  - logs\\agent.log: newest NON-ambient line within RECENT_WINDOW     (root turn liveness,
    ambient-filtered — see v3 notes)
  - kanban\\logs\\*.log modified within RECENT_WINDOW                 (worker output liveness)
  - kanban.db tasks in running/claimed                              (THE strong signal)
  - profiles\\*\\state.db: turn leases + recent messages              (bridge sessions
    & dispatched kanban workers — they run on profile homes, invisibly to root)

v2 (2026-10-12) fixes + additions:
  * FIXED a silent no-op: the kanban signal read kanban\\kanban.db — a 0-byte
    decoy — so "a card is running" never pinned the machine awake (this is the
    root cause of the 10-11 night sleep mid-card). Now reads the LIVE DB at
    hermes\\kanban.db. Verified: --once now reports kanban:N while a card runs.
  * ADDED per-profile state.db scan (leases + recent messages) for the six
    bridge homes, so worker sessions are visible even between log writes.
  * ADDED single-instance guard (named mutex): duplicate daemons log and exit.
  * DELIBERATELY NOT a signal: profiles\\*\\logs recency — those files get a
    synchronized ~60s touch from a background writer (all six profiles show
    the same mtime age), so recency there would pin the machine awake forever.
  * SetThreadExecutionState return value now checked (WARN on failure).

v3 (2026-10-12 evening) — the mechanism actually fixes "workbench open => PC never
does a real idle sleep", after kernel evidence (Kernel-Power 506/507) showed the
machine entered Connected Standby at 18:59/19:56/20:47 WHILE the ES hold was
active: on this Dell G15 / S0 platform, ES_SYSTEM_REQUIRED alone does NOT block
idle standby entry. Changes:
  * PRIMARY MECHANISM: AC "sleep after" timeout toggle, no admin required.
      busy   -> powercfg /setacvalueindex SCHEME_CURRENT SUB_SLEEP STANDBYIDLE 0
      idle   -> restore the value read before the hold (300s here)
    The OS then refuses idle sleep itself; the display timeout is untouched
    (screen can still turn off while work continues). ES hold kept as
    belt-and-braces (it does its job on machines that honor it).
  * SAFETY: the pre-hold value is persisted to keepawake-power.json (with an
    owner pid+creation-time stamp); a stale applied-hold left by a dead daemon
    is released at startup; restores never guess a value — they only write the
    stored original back, verify by read-back, and yield to manual changes;
    90-keepawake.cmd :stop / :release also restore (via --restore).
  * v3.1: single-instance mutex under Global (Local fallback); powercfg calls
    judge exit codes; AC/DC parsed by label with the positional old fallback;
    DB errors degrade to warnings after ~10 failing ticks; keepawake.log
    rotates at 2 MB; the drift guard runs on wall-clock (~10 min).
  * agent.log signal is now CONTENT-AWARE: housekeeping writers seen pinning the
    machine via the old mtime check (profile reconcile every ~60s, session
    cleanup timers ~5 min after a session ends, stray "deadline timed out"
    lines) are ignored; only "real" lines (turns/tools/api/errors) count.
  * While busy, the timeout toggle is re-asserted every ~10 min (drift guard).

Usage:
  pythonw 80-task-keepawake.py           # daemon (no console); single instance
  python  80-task-keepawake.py --once    # print one decision (JSON) and exit

Control shell: .build\\workbench\\90-keepawake.cmd [status|hold|release|start|stop]
"""
import atexit
import ctypes
import datetime
import json
import os
import pathlib
import re
import signal
import sqlite3
import subprocess
import sys
import time

HOME = pathlib.Path(os.environ.get('LOCALAPPDATA', r'C:\Users\<用户名>\AppData\Local')) / 'hermes'
STATE = HOME / 'state.db'
KANBAN = HOME / 'kanban.db'            # LIVE db; hermes\kanban\kanban.db is a 0-byte decoy — never use it
KANBAN_LOGS = HOME / 'kanban' / 'logs'
PROFILES = HOME / 'profiles'
AGENT_LOG = HOME / 'logs' / 'agent.log'
FLAG_ON = HOME / 'keep-awake.on'
LOGP = HOME / 'logs' / 'keepawake.log'
POWER_FILE = HOME / 'keepawake-power.json'

INTERVAL = 30
RECENT_WINDOW = 150          # seconds; message/log recency that means "busy"
ACTIVE_DELEGATION_STATES = ('pending', 'dispatched', 'running', 'claimed', 'delivering')
KANBAN_BUSY_STATES = ('running', 'claimed')

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001

# Housekeeping writers into logs\agent.log that are NOT work. Observed sources:
#   gateway profile reconcile ("MCP servers reconciled with config", "Re-scanned profile"),
#   session teardown timers ("Cleaned up inactive environment ..."), stray deadline
#   warnings, lease pruning, multiplex scope warnings.
AMBIENT_RE = re.compile(
    r'(MCP servers reconciled with config'
    r'|Re-scanned profile'
    r'|Cleaned up inactive environment'
    r'|timed out after'
    r'|Pruned \d+ stale active session lease'
    r'|no profile secret scope)'
)
AGENTLOG_MAX_BYTES = 150_000
AGENTLOG_MAX_LINES = 500
_NO_WINDOW = 0x08000000

_MUTEX_NAME = 'Global\\HermesKeepAwake80'  # cross-session single-instance guard
_MUTEX_NAME_LOCAL = 'Local\\HermesKeepAwake80'
_mutex_handle = None                       # module-level: keeps the mutex alive

_LOGP_MAX_BYTES = 2 * 1024 * 1024          # keepawake.log rotation threshold
_db_err_streak = {}                        # tag -> consecutive failing ticks
_DB_ERR_LIMIT = 10                         # after that many ticks: warning-only


def _db_err(reasons, warnings, tag, e):
    n = _db_err_streak.get(tag, 0) + 1
    _db_err_streak[tag] = n
    if n <= _DB_ERR_LIMIT:
        reasons.append('%s-err:%s' % (tag, e))
    else:
        warnings.append('%s-err degraded (tick %d, still counted as busy): %s' % (tag, n, e))


def _db_ok(tag):
    _db_err_streak[tag] = 0


def _proc_create_time(pid):
    """Process creation time (unix seconds) via GetProcessTimes, or None."""
    try:
        k32 = ctypes.windll.kernel32
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        h = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
        if not h:
            return None
        try:
            creation = ctypes.c_ulonglong(0)
            exit_t = ctypes.c_ulonglong(0)
            kernel = ctypes.c_ulonglong(0)
            user = ctypes.c_ulonglong(0)
            ok = k32.GetProcessTimes(h, ctypes.byref(creation), ctypes.byref(exit_t),
                                     ctypes.byref(kernel), ctypes.byref(user))
            if not ok:
                return None
            return creation.value / 1e7 - 11644473600.0
        finally:
            k32.CloseHandle(h)
    except Exception:
        return None


def _owner_alive(owner):
    """True when the recorded holder process (pid + creation time) still runs."""
    try:
        pid = int((owner or {}).get('pid') or 0)
    except Exception:
        return False
    if not pid:
        return False
    ct = _proc_create_time(pid)
    if ct is None:
        return False
    rec = (owner or {}).get('ctime')
    if rec is not None:
        try:
            if abs(ct - float(rec)) > 2:
                return False           # pid reused by an unrelated process
        except Exception:
            pass
    return True


def log(msg):
    try:
        try:
            if LOGP.exists() and LOGP.stat().st_size > _LOGP_MAX_BYTES:
                bak = LOGP.parent / (LOGP.name + '.1')
                try:
                    if bak.exists():
                        bak.unlink()
                except Exception:
                    pass
                os.replace(LOGP, bak)
        except Exception:
            pass
        with open(LOGP, 'a', encoding='utf-8') as fh:
            fh.write('%s %s\n' % (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), msg))
    except Exception:
        pass


def db_ro(p):
    return sqlite3.connect('file:%s?mode=ro' % pathlib.PurePath(p).as_posix(), uri=True, timeout=3.0)


def _recent_file_age(p, now):
    try:
        if p.exists():
            return now - p.stat().st_mtime
    except Exception:
        pass
    return None


def _agentlog_probe(now):
    """Content-aware agent.log liveness. Returns (reason|None, note|None).

    Only non-ambient lines (real turn/tool activity) within RECENT_WINDOW count;
    ambient housekeeping lines are ignored so periodic writers cannot pin the
    machine awake. On unreadable input it fails TOWARDS activity (mtime check)
    so a log hiccup can never cause a mid-work sleep.
    """
    try:
        if not AGENT_LOG.exists():
            return None, None
        size = AGENT_LOG.stat().st_size
        with open(AGENT_LOG, 'rb') as fh:
            if size > AGENTLOG_MAX_BYTES:
                fh.seek(size - AGENTLOG_MAX_BYTES)
                raw = fh.read()
                cut = raw.find(b'\n')
                raw = raw[cut + 1:] if cut >= 0 else raw
            else:
                raw = fh.read()
        text = raw.decode('utf-8', errors='replace')
        newest_real = None
        newest_ambient = None
        for line in text.splitlines()[-AGENTLOG_MAX_LINES:]:
            if len(line) < 19:
                continue
            try:
                ts = datetime.datetime.strptime(line[:19], '%Y-%m-%d %H:%M:%S').timestamp()
            except Exception:
                continue
            if not (0 <= now - ts <= 3600):
                continue
            if AMBIENT_RE.search(line):
                if newest_ambient is None or ts > newest_ambient:
                    newest_ambient = ts
            else:
                if newest_real is None or ts > newest_real:
                    newest_real = ts
        if newest_real is not None and (now - newest_real) < RECENT_WINDOW:
            return 'agentlog:%.0fs' % (now - newest_real), None
        if newest_ambient is not None and (now - newest_ambient) < RECENT_WINDOW:
            return None, 'agentlog ambient-only (%.0fs ago; ignored)' % (now - newest_ambient)
        return None, None
    except Exception as e:
        age = _recent_file_age(AGENT_LOG, now)
        if age is not None and 0 <= age < RECENT_WINDOW:
            return 'agentlog-mtime:%.0fs' % age, 'agentlog probe fallback: %r' % e
        return None, 'agentlog probe err: %r' % e


def _run_powercfg(args):
    """Run powercfg windowless; returns (stdout_text|None, err|None, returncode|None).
    No admin needed for the query/setacvalueindex/setactive verbs used here."""
    try:
        r = subprocess.run(['powercfg'] + args, capture_output=True,
                           creationflags=_NO_WINDOW, timeout=25)
    except Exception as e:
        return None, repr(e), None
    return r.stdout.decode('mbcs', errors='replace'), None, r.returncode


def _powercfg_ac_sec():
    """Current AC 'sleep after' (STANDBYIDLE) in seconds, or None on query/parse failure."""
    out, _err, rc = _run_powercfg(['/query', 'SCHEME_CURRENT', 'SUB_SLEEP', 'STANDBYIDLE'])
    if out is None or rc != 0:
        return None
    # parse by label first (works for both English and Chinese powercfg output);
    # fall back to the old "last two 0x values" strategy.
    ac = None
    for tag, val in re.findall(r'(AC|DC|\u4ea4\u6d41|\u76f4\u6d41)[^\r\n]*?0x([0-9a-fA-F]{1,8})', out):
        if tag in ('AC', '\u4ea4\u6d41') and ac is None:
            try:
                ac = int(val, 16)
            except ValueError:
                ac = None
    if ac is not None:
        return ac
    vals = re.findall(r'0x([0-9a-fA-F]{1,8})', out)
    if len(vals) >= 2:
        try:
            return int(vals[-2], 16)          # last two 0x values = AC, then DC
        except ValueError:
            return None
    return None


def _powercfg_set_ac_sec(sec):
    out, _err, rc = _run_powercfg(['/setacvalueindex', 'SCHEME_CURRENT', 'SUB_SLEEP', 'STANDBYIDLE', str(int(sec))])
    if out is None or rc != 0:
        log('WARN powercfg setacvalueindex failed (rc=%r)' % rc)
        return False
    out2, _err2, rc2 = _run_powercfg(['/setactive', 'SCHEME_CURRENT'])
    if out2 is None or rc2 != 0:
        log('WARN powercfg setactive failed (rc=%r)' % rc2)
        return False
    return True


def _power_state_load():
    try:
        return json.loads(POWER_FILE.read_text(encoding='utf-8'))
    except Exception:
        return None


def _power_state_save(d):
    try:
        POWER_FILE.write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')
    except Exception:
        pass


def _save_applied(orig):
    _power_state_save({'applied': True, 'ac_orig_sec': int(orig),
                       'owner': {'pid': os.getpid(),
                                 'ctime': _proc_create_time(os.getpid()),
                                 'at': time.time()}})


def _power_hold_engage():
    """Busy -> set AC sleep timeout to 0 (never). Idempotent + self-repairing."""
    st = _power_state_load() or {}
    if st.get('applied'):
        cur = _powercfg_ac_sec()
        if cur == 0:
            return
        if _powercfg_set_ac_sec(0) and _powercfg_ac_sec() == 0:
            log('POWER re-applied standby-timeout-ac=0')
        else:
            log('WARN standby-timeout-ac re-apply failed')
        return
    cur = _powercfg_ac_sec()
    if cur is None:
        log('WARN powercfg query failed; ES hold only this cycle')
        return
    if cur == 0:
        _save_applied(0)
        log('POWER standby-timeout-ac already 0; marked held')
        return
    _save_applied(cur)
    if _powercfg_set_ac_sec(0) and _powercfg_ac_sec() == 0:
        log('POWER standby-timeout-ac %ss -> 0 (system cannot idle-sleep)' % cur)
    else:
        log('WARN standby-timeout-ac set failed; ES hold only (orig %ss kept)' % cur)


def _power_hold_release(reason='idle'):
    """Idle -> restore the pre-hold AC sleep timeout, safely.

    Never guesses: without a valid stored pre-hold value nothing is written
    back. The restore only happens while the current value is still 0 (what
    this daemon wrote), so a manual change during the hold wins; the result is
    verified by read-back before the state is marked released.
    """
    st = _power_state_load() or {}
    if not st.get('applied'):
        return
    orig = st.get('ac_orig_sec')
    if not isinstance(orig, int) or not (0 <= orig <= 7 * 86400):
        log('WARN power release(%s): stored ac_orig_sec=%r invalid; NOT writing back — check the AC standby timeout manually' % (reason, st.get('ac_orig_sec')))
        return
    cur = _powercfg_ac_sec()
    if cur is None:
        log('WARN power release(%s): powercfg query failed; hold kept for next cycle' % reason)
        return
    if cur != 0:
        log('power release(%s): AC is %ss (not the 0 we wrote; changed manually?) — keep it, clear hold state' % (reason, cur))
        _power_state_save({'applied': False, 'ac_orig_sec': orig})
        return
    if not _powercfg_set_ac_sec(orig):
        log('WARN power release(%s): restore write failed; hold kept for next cycle' % reason)
        return
    back = _powercfg_ac_sec()
    if back != orig:
        log('WARN power release(%s): read-back mismatch (want %ss, got %r); retry next cycle' % (reason, orig, back))
        return
    _power_state_save({'applied': False, 'ac_orig_sec': orig})
    log('POWER standby-timeout-ac restored to %ss (%s)' % (orig, reason))


def _power_hold_reconcile():
    """Startup self-check: an applied hold whose owner process is gone is stale
    (the previous daemon was killed without cleanup) — release it now. Live
    owners (another instance) are left alone."""
    st = _power_state_load() or {}
    if not st.get('applied'):
        return
    owner = st.get('owner') or {}
    if _owner_alive(owner):
        return
    log('startup reconcile: stale power hold (owner pid %r not running) -> releasing' % owner.get('pid'))
    _power_hold_release('startup-reconcile')


def _at_exit():
    try:
        st = _power_state_load() or {}
        if st.get('applied'):
            _power_hold_release()
    except Exception:
        pass


# NOTE: atexit registration happens in main() (daemon branch) ONLY — an --once
# probe must never run the cleanup, or it would release a live daemon's hold.


def _probe_profile_dbs(now, reasons, warnings):
    """leases + recent messages from every profile home state.db.

    Profile errors only go to warnings (they must never pin the machine awake —
    e.g. a profile db with an older schema would otherwise hold forever).
    """
    try:
        if not PROFILES.exists():
            return
        for sp in sorted(PROFILES.glob('*/state.db')):
            name = sp.parent.name
            if name.startswith('.'):
                continue
            try:
                con = db_ro(sp)
                try:
                    r = con.execute('SELECT COUNT(*) FROM session_turn_leases WHERE expires_at > ?',
                                    (now,)).fetchone()
                    if r and r[0]:
                        reasons.append('p:%s-lease:%d' % (name, r[0]))
                    r = con.execute('SELECT MAX(timestamp) FROM messages').fetchone()
                    if r and r[0]:
                        age = now - float(r[0])
                        if 0 <= age < RECENT_WINDOW:
                            reasons.append('p:%s-msg:%.0fs' % (name, age))
                finally:
                    con.close()
            except Exception as e:
                warnings.append('p:%s-err:%s' % (name, e))
    except Exception as e:
        warnings.append('profiles-scan-err:%s' % e)


def check_once():
    """Return (reasons, warnings): reasons non-empty => the machine is busy."""
    now = time.time()
    reasons = []
    warnings = []

    # 1) explicit flag file (manual hold)
    try:
        if FLAG_ON.exists():
            reasons.append('flag:keep-awake.on')
    except Exception:
        pass

    # 2) root state.db signals
    if STATE.exists():
        try:
            con = db_ro(STATE)
            try:
                r = con.execute('SELECT COUNT(*) FROM session_turn_leases WHERE expires_at > ?', (now,)).fetchone()
                if r and r[0]:
                    reasons.append('leases:%d' % r[0])
                r = con.execute('SELECT MAX(timestamp) FROM messages').fetchone()
                if r and r[0]:
                    age = now - float(r[0])
                    if 0 <= age < RECENT_WINDOW:
                        reasons.append('activity:%.0fs' % age)
                ph = ','.join('?' * len(ACTIVE_DELEGATION_STATES))
                r = con.execute('SELECT COUNT(*) FROM async_delegations WHERE state IN (%s)' % ph,
                                ACTIVE_DELEGATION_STATES).fetchone()
                if r and r[0]:
                    reasons.append('delegations:%d' % r[0])
                _db_ok('state.db')
            finally:
                con.close()
        except Exception as e:
            _db_err(reasons, warnings, 'state.db', e)

    # 2b) per-profile state.db signals (bridge sessions & dispatched kanban workers)
    _probe_profile_dbs(now, reasons, warnings)

    # 3) log liveness: root agent log (content-aware, ambient-filtered) + worker logs
    try:
        reason, note = _agentlog_probe(now)
        if reason:
            reasons.append(reason)
        if note:
            warnings.append(note)
    except Exception as e:
        warnings.append('agentlog-probe-err:%s' % e)
    try:
        if KANBAN_LOGS.exists():
            for p in KANBAN_LOGS.glob('*.log'):
                age = _recent_file_age(p, now)
                if age is not None and 0 <= age < RECENT_WINDOW:
                    reasons.append('worklog:%s' % p.name)
                    break
    except Exception:
        pass

    # 4) kanban task states (LIVE db)
    try:
        if KANBAN.exists() and KANBAN.stat().st_size > 0:
            con = db_ro(KANBAN)
            try:
                ph = ','.join('?' * len(KANBAN_BUSY_STATES))
                r = con.execute('SELECT COUNT(*) FROM tasks WHERE status IN (%s)' % ph,
                                KANBAN_BUSY_STATES).fetchone()
                if r and r[0]:
                    reasons.append('kanban:%d' % r[0])
                _db_ok('kanban')
            finally:
                con.close()
    except Exception as e:
        _db_err(reasons, warnings, 'kanban', e)

    return reasons, warnings


def _acquire_single_instance():
    """Named-mutex single-instance guard (Global scope, Local fallback).
    Returns True when we own the mutex."""
    global _mutex_handle
    for name in (_MUTEX_NAME, _MUTEX_NAME_LOCAL):
        try:
            k32 = ctypes.WinDLL('kernel32', use_last_error=True)
            k32.CreateMutexW.restype = ctypes.c_void_p
            h = k32.CreateMutexW(None, False, name)
            if h:
                if ctypes.get_last_error() != 183:  # 183 = ERROR_ALREADY_EXISTS
                    _mutex_handle = h
                    return True
                try:
                    ctypes.windll.kernel32.CloseHandle(h)
                except Exception:
                    pass
                return False                 # an instance already holds this scope
            log('WARN CreateMutexW(%s) failed; trying next scope' % name)
        except Exception as e:
            log('WARN mutex guard raised %r (trying next scope)' % e)
    log('WARN single-instance guard unavailable (fail-open)')
    return True                          # a guard failure must not disable keep-awake


def _set_state(flags, what):
    try:
        rv = ctypes.windll.kernel32.SetThreadExecutionState(flags)
        if not rv:
            log('WARN SetThreadExecutionState(%s) failed err=%s'
                % (what, ctypes.windll.kernel32.GetLastError()))
    except Exception as e:
        log('WARN SetThreadExecutionState(%s) raised %r' % (what, e))


def main():
    if '--once' in sys.argv:
        reasons, warnings = check_once()
        try:
            pstate = _power_state_load()
        except Exception:
            pstate = None
        print(json.dumps({'busy_reasons': reasons, 'warnings': warnings,
                          'power': {'ac_sec': _powercfg_ac_sec(), 'state': pstate},
                          'ts': datetime.datetime.now().isoformat()}, ensure_ascii=False))
        return
    if '--restore' in sys.argv:
        st = _power_state_load() or {}
        if not st.get('applied'):
            print('no hold applied (nothing to restore)')
            return
        owner = st.get('owner') or {}
        if _owner_alive(owner):
            print('owner daemon still running (pid %r); not touching' % owner.get('pid'))
            return
        _power_hold_release('manual-restore')
        st2 = _power_state_load() or {}
        print(json.dumps({'applied': st2.get('applied'), 'ac_sec': _powercfg_ac_sec()}, ensure_ascii=False))
        return
    if not _acquire_single_instance():
        log('duplicate instance detected -- exit (mutex %s already held)' % _MUTEX_NAME)
        return

    def _sigterm(_signum, _frame):
        raise SystemExit(0)
    try:
        signal.signal(signal.SIGTERM, _sigterm)
    except Exception:
        pass
    atexit.register(_at_exit)   # daemon branch only; releases the power hold on graceful exit
    _power_hold_reconcile()     # v3.1: release a stale hold left by a dead daemon

    log('daemon start pid=%s interval=%ss v3.1 (standby-timeout toggle + ES)' % (os.getpid(), INTERVAL))
    holding = None
    last_engage_wall = 0.0
    while True:
        try:
            reasons, warnings = check_once()
            busy = bool(reasons)
            if busy:
                _set_state(ES_CONTINUOUS | ES_SYSTEM_REQUIRED, 'hold')
                if holding is not True:
                    log('HOLD  ' + ';'.join(reasons))
                    for w in warnings:
                        log('  warn ' + w)
                    _power_hold_engage()
                    last_engage_wall = time.time()
                elif time.time() - last_engage_wall > 600:
                    _power_hold_engage()          # drift guard (wall-clock, ~10 min)
                    last_engage_wall = time.time()
            else:
                _set_state(ES_CONTINUOUS, 'release')
                if holding is not False:
                    log('RELEASE (idle)')
                    for w in warnings:
                        log('  warn ' + w)
                    _power_hold_release('idle')
            holding = busy
        except Exception as e:
            log('ERROR ' + repr(e))
        time.sleep(INTERVAL)


if __name__ == '__main__':
    main()
