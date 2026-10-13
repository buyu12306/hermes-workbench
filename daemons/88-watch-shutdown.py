# -*- coding: utf-8 -*-
"""88-watch-shutdown.py — 任务完成后自动关机守护（保底，v2 安全版）

- 轮询 kanban DB 中指定任务的状态；
- 只有 done/completed 视为“完成激发”；blocked 不再触发关机（等决策时最不该关机）；
- 进入完成态：等 GRACE_MIN 分钟（期间每 45s 复查，卡被重开立即取消）；
- 宽限结束/清醒超时后，先查全局是否还有 running/claimed 的卡——有就顺延或不关机
  （2026-10-12 误关机教训）；DB 读取失败按“最保守”处理（不关机）；
- 关机命令不带 -f；倒计时被取消或未能生效则继续监控、绝不自动重发；
- “清醒时长”用 QueryUnbiasedInterruptTime（不计睡眠），不可用时退回
  “>300s 空档过滤”旧算法；DB 连续报错时暂停计时并告警；
- 任务不存在于 DB → 直接退出（无事可看）。
用法: python 88-watch-shutdown.py <task_id> [grace_min] [deadline_h]
"""
import ctypes
import datetime
import os
import sqlite3
import subprocess
import sys
import time

TID = sys.argv[1] if len(sys.argv) > 1 else ''
GRACE_MIN = float(sys.argv[2]) if len(sys.argv) > 2 else 40.0
DEADLINE_H = float(sys.argv[3]) if len(sys.argv) > 3 else 7.0

_LOCAL = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
DB = os.path.join(_LOCAL, 'hermes', 'kanban.db').replace(os.sep, '/')
LOG = 'C:/Users/<用户名>/Desktop/工作区/Hermes工作台/shared/minidayz/shutdown-supervisor.log'
if not os.path.isdir(os.path.dirname(LOG)):
    LOG = os.path.join(_LOCAL, 'hermes', 'logs', 'shutdown-supervisor.log')
    os.makedirs(os.path.dirname(LOG), exist_ok=True)

TERM = {'done', 'completed'}            # R88-2: only a real finish arms the shutdown
ACTIVE = ('running', 'claimed')         # global actives that veto a shutdown

logf = open(LOG, 'a', encoding='utf-8')


def logp(*a):
    line = '%s %s' % (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                      ' '.join(str(x) for x in a))
    print(line, file=logf, flush=True)


def _db():
    return sqlite3.connect('file:%s?mode=ro' % DB, uri=True, timeout=5.0)


def get_status():
    try:
        con = _db()
        row = con.execute('SELECT status FROM tasks WHERE id=?', (TID,)).fetchone()
        con.close()
        return row[0] if row else 'missing'
    except Exception as e:
        return 'dberr:%s' % e


def count_active():
    """running/claimed global count; -1 = DB unreadable (treat as 'active', fail-safe)."""
    try:
        con = _db()
        ph = ','.join('?' * len(ACTIVE))
        row = con.execute('SELECT COUNT(*) FROM tasks WHERE status IN (%s)' % ph, ACTIVE).fetchone()
        con.close()
        return int(row[0]) if row else 0
    except Exception:
        return -1


def _unbiased():
    try:
        v = ctypes.c_ulonglong(0)
        if ctypes.windll.kernel32.QueryUnbiasedInterruptTime(ctypes.byref(v)):
            return v.value / 1e7
    except Exception:
        pass
    return None


def do_shutdown(reason):
    logp('SHUTDOWN ->', reason)
    try:
        r = subprocess.run(['shutdown.exe', '-s', '-t', '120'], capture_output=True,
                           text=True, timeout=30)
    except Exception as e:
        logp('shutdown.exe failed:', e)
        return
    out = ((r.stdout or '') + (r.stderr or '')).strip()
    logp('shutdown.exe rc=%s %s' % (r.returncode, out[:200]))
    if r.returncode != 0:
        logp('shutdown NOT accepted; keep watching (no auto re-issue)')
        return
    time.sleep(150)                     # countdown is 120s; still alive => cancelled/blocked
    try:
        r2 = subprocess.run(['shutdown.exe', '-a'], capture_output=True, text=True, timeout=30)
        if r2.returncode == 0:
            logp('pending shutdown found and aborted -> was cancelled late; keep watching')
        else:
            logp('countdown elapsed but machine still up -> cancelled/blocked; keep watching')
    except Exception as e:
        logp('post-shutdown probe failed:', e)
    logp('auto-shutdown will NOT be re-issued this run')


logp('watch-shutdown start: task=%s grace=%smin deadline=%sh (unbiased awake-time)' % (TID, GRACE_MIN, DEADLINE_H))
if not TID:
    logp('no task id given -> exit')
    sys.exit(2)

awake = 0.0
ub_last = _unbiased()
last_t = time.time()
last = None
derr = 0
shutdown_done = False

while True:
    st = get_status()
    if st != last:
        logp('status:', st)
        last = st
    now = time.time()
    ub = _unbiased()
    healthy = st != 'missing' and not (isinstance(st, str) and st.startswith('dberr'))
    if ub is not None:
        delta = ub - ub_last if ub_last is not None else 0.0
        ub_last = ub
        if healthy and delta >= 0:
            awake += delta
    else:
        ub_last = None
        step = now - last_t
        if healthy:
            if step > 300:
                logp('suspend gap ignored: %.0fs (not counted)' % step)
            else:
                awake += step
    last_t = now

    if st == 'missing':
        logp('task %s not in DB -> exit' % TID)
        break
    if isinstance(st, str) and st.startswith('dberr'):
        derr += 1
        if derr == 1 or derr % 10 == 0:
            logp('db error (#%d): %s -- timer paused, still watching' % (derr, st))
    else:
        derr = 0

    if st in TERM and not shutdown_done:
        logp('terminal state reached; grace %s min (re-checking every 45s)' % GRACE_MIN)
        grace_end = time.time() + GRACE_MIN * 60
        left_terminal = False
        while time.time() < grace_end:
            time.sleep(45)
            st2 = get_status()
            if st2 not in TERM:
                logp('card left terminal during grace (now %s) -> shutdown cancelled' % st2)
                left_terminal = True
                break
        if not left_terminal:
            act = count_active()
            if act != 0:
                why = 'DB read error (fail-safe)' if act == -1 else '%d active card(s) globally' % act
                logp('grace over but %s -> NOT shutting down this run' % why)
            else:
                do_shutdown('terminal=%s' % st)
            shutdown_done = True

    if awake > DEADLINE_H * 3600 and not shutdown_done:
        act = count_active()
        if act != 0:
            why = 'DB read error (fail-safe)' if act == -1 else '%d active card(s)' % act
            logp('awake-deadline hit (status=%s) but %s -> extend 30 min' % (st, why))
            awake = DEADLINE_H * 3600 - 1800
        else:
            do_shutdown('awake-deadline %sh reached, status=%s' % (DEADLINE_H, st))
            shutdown_done = True

    time.sleep(60)
