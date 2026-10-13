"""Watch kanban cards until they reach a terminal status. One OS process, no LLM.

Usage: python 87-watch-cards.py [id1 id2 [hours]]
Polls the kanban DB read-only every 90s and exits when all listed cards are
done/completed/blocked/failed/cancelled (or on timeout). Intended to be started
with the terminal tool as background=True, notify=True so completion fires a
notification into the conversation.
"""
import re
import sqlite3
import sys
import time

DB = r"C:\Users\<用户名>\AppData\Local\hermes\kanban.db"  # NOTE: ...\hermes\kanban\kanban.db is an EMPTY decoy
_args = sys.argv[1:]
_hours = 3.0
if _args and re.match(r"^\d+(\.\d+)?$", _args[-1]):
    _hours = float(_args.pop())
if not _args:
    print("usage: 87-watch-cards.py <task_id> [task_id ...] [hours]  (no default cards)", flush=True)
    sys.exit(2)
ids = _args
hours = _hours
TERMINAL = {"done", "completed", "blocked", "failed", "cancelled"}


def statuses(cur):
    out = {}
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    tname = None
    for t in tables:
        try:
            cols = [c[1] for c in cur.execute("PRAGMA table_info(%s)" % t).fetchall()]
        except Exception:
            continue
        if "id" in cols and "status" in cols:
            tname = t
            if t == "tasks":
                break
    if not tname:
        return {"_": "no status table"}
    for tid in ids:
        r = cur.execute("SELECT status FROM %s WHERE id=?" % tname, (tid,)).fetchone()
        out[tid] = r[0] if r else "missing"
    return out


deadline = time.time() + hours * 3600
while True:
    try:
        con = sqlite3.connect("file:%s?mode=ro" % DB, uri=True)
        st = statuses(con.cursor())
        con.close()
        print(time.strftime("%H:%M:%S"), st, flush=True)
        if all(str(st.get(t, "")).lower() in TERMINAL for t in ids):
            print("ALL TERMINAL:", st, flush=True)
            break
    except Exception as e:
        print("poll error:", repr(e), flush=True)
    if time.time() > deadline:
        print("TIMEOUT reached", flush=True)
        break
    time.sleep(90)
print("watcher done")
