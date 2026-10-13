"""Workbench Graph — backend API for the desktop workflow-graph plugin.

Read-only view over the shared kanban board (`hermes_cli.kanban_db` — the same
code paths the CLI and the bundled kanban dashboard use), mounted at
`/api/plugins/workbench-graph/`. Consumed by `desktop-plugins/workbench-graph/`.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Body, HTTPException, Query

router = APIRouter()

_BOARD_Q = Query(None, description="Kanban board slug (omit for current)")

# board 白名单：board 参与看板库路径解析（kanban_db_path(board=...)），这里只放行
# 合法 slug 字符集，越界输入直接 400，不给核心层路径解析留下额外输入面。
_BOARD_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _valid_board(board: Optional[str]) -> Optional[str]:
    if board is None:
        return None
    b = str(board).strip()
    if not b:
        return None
    if not _BOARD_RE.match(b):
        raise HTTPException(status_code=400, detail="非法 board 参数")
    return b

# Statuses rendered by the graph UI, in pipeline order.
_PIPELINE = ("triage", "todo", "scheduled", "ready", "running", "review", "blocked", "done")

# Desktop agent software shown in the graph's "外部智能体" row.
# (id, display name, candidate paths — the first existing one wins.)
_EXTERNALS = (
    ("claude-code", "Claude Code", (r"%USERPROFILE%\.claude\vscode-claude-code.cmd", r"%APPDATA%\npm\claude.cmd", r"%APPDATA%\npm\claude")),
    ("qoder", "Qoder", (r"%LOCALAPPDATA%\Qoder CN\Qoder CN Launcher\Qoder CN Launcher.exe",)),
    ("trae", "Trae", (r"%USERPROFILE%\Desktop\Trae CN\Trae CN.exe",)),
    ("trae-solo", "TRAE SOLO", (r"%USERPROFILE%\Desktop\TRAE SOLO CN\TRAE SOLO CN.exe",)),
    ("deepseek-harness", "DeepSeek Harness", (r"%LOCALAPPDATA%\Programs\DeepSeek Harness\DeepSeek Harness.exe",)),
    ("workbuddy", "WorkBuddy", (r"%LOCALAPPDATA%\Programs\WorkBuddy\WorkBuddy.exe",)),
)


def _externals_payload() -> list:
    out = []
    for eid, name, candidates in _EXTERNALS:
        hit = None
        for cand in candidates:
            p = os.path.expandvars(cand)
            if os.path.exists(p):
                hit = p
                break
        out.append({"id": eid, "name": name, "ok": hit is not None, "path": hit or os.path.expandvars(candidates[0])})
    return out


def _known_assignees() -> set:
    """建卡白名单：外部智能体 id + hermes profiles 目录下已有 profile 名。"""
    ids = {e[0] for e in _EXTERNALS}
    try:
        from hermes_constants import get_hermes_home
        pdir = os.path.join(str(get_hermes_home()), "profiles")
        if os.path.isdir(pdir):
            ids.update(d for d in os.listdir(pdir) if os.path.isdir(os.path.join(pdir, d)))
    except Exception:
        pass
    return ids


def _task_dict(t: Any) -> dict:
    return {
        "status": t.status,
        "assignee": t.assignee,
        "completed_at": t.completed_at,
    }


@router.get("/")
def health() -> dict:
    return {"ok": True, "plugin": "workbench-graph"}


@router.get("/tasks")
def tasks(
    board: Optional[str] = _BOARD_Q,
    limit: int = Query(1000, ge=1, le=1000),
) -> dict:
    from hermes_cli import kanban_db as kb
    from hermes_cli import kanban_db_connect as kbc

    board = _valid_board(board)
    with kbc.connect_closing(board=board) as conn:
        # created-desc: truncation (LIMIT) must keep the NEWEST n tasks, or new cards go
        # invisible once the board exceeds the limit. (opt-round 2026-10-09)
        items = kb.list_tasks(conn, limit=int(limit), order_by="created-desc")
        by_status = {r["status"]: r["c"] for r in conn.execute("SELECT status, COUNT(*) AS c FROM tasks WHERE status != 'archived' GROUP BY status")}

    return {
        "ok": True,
        "board": board if board is not None else kb.get_current_board(),
        "count": len(items),
        "by_status": by_status,
        "pipeline": list(_PIPELINE),
        "tasks": [_task_dict(t) for t in items],
    }


@router.get("/summary")
def summary(board: Optional[str] = _BOARD_Q) -> dict:
    """Aggregate-only view for the graph: status counts + per-assignee status counts
    + per-assignee max(completed_at). Whole table via GROUP BY — no limit cliff,
    no per-card payload growth. ~0.5KB regardless of board size."""
    from hermes_cli import kanban_db as kb
    from hermes_cli import kanban_db_connect as kbc

    board = _valid_board(board)
    with kbc.connect_closing(board=board) as conn:
        by_status: dict[str, int] = {}
        agents: dict[str, dict] = {}
        for row in conn.execute(
            "SELECT assignee, status, COUNT(*) AS c, MAX(completed_at) AS last_done "
            "FROM tasks WHERE status != 'archived' GROUP BY assignee, status"
        ):
            st, cnt, last = row["status"], int(row["c"]), int(row["last_done"] or 0)
            by_status[st] = by_status.get(st, 0) + cnt
            if row["assignee"]:
                a = agents.setdefault(str(row["assignee"]), {"counts": {}, "last_done": 0})
                a["counts"][st] = a["counts"].get(st, 0) + cnt
                a["last_done"] = max(a["last_done"], last)

    return {
        "ok": True,
        "board": board if board is not None else kb.get_current_board(),
        "by_status": by_status,
        "pipeline": list(_PIPELINE),
        "agents": agents,
    }


@router.get("/externals")
def externals() -> dict:
    return {"ok": True, "externals": _externals_payload()}


# --- balances: each software's OWN account balance / credits -----------------
# The point: money/credits come from the software's own account (its own
# credential store), never from the Hermes model key.

_BAL_TTL = 1800.0
_BAL_CACHE: dict = {"t": 0.0, "data": None}
_BAL_LOCK = threading.Lock()


def _fmt_money(i: Any) -> str:
    cur = str((i or {}).get("currency") or "CNY")
    amt = str((i or {}).get("total_balance", "?"))
    return ("人民币 " if cur.upper() == "CNY" else cur + " ") + amt


def _log_exc(where: str, e: Exception) -> None:
    """异常细节落盘（logs/workbench-graph.log）；界面只给中文提示，不带英文异常名。"""
    try:
        base = None
        try:
            from hermes_constants import get_hermes_home
            base = str(get_hermes_home())
        except Exception:
            base = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "hermes")
        p = os.path.join(base, "logs", "workbench-graph.log")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "a", encoding="utf-8") as fh:
            fh.write("%s [%s] %s: %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), where, type(e).__name__, str(e)[:300]))
    except Exception:
        pass


def _deepseek_balance() -> dict:
    """Balance of the DeepSeek account configured INSIDE DeepSeek Harness (~/.dsh)."""
    try:
        import urllib.request

        from hermes_cli.profiles import _load_yaml_dict
        creds = _load_yaml_dict(Path(os.path.join(os.path.expanduser("~"), ".dsh", ".credentials.yaml"))) or {}
        key = str((creds.get("refs") or {}).get("DEEPSEEK_API_KEY") or "")
        if not key:
            return {"status": "login", "text": "未配置"}
        req = urllib.request.Request(
            "https://api.deepseek.com/user/balance",
            headers={"Authorization": "Bearer " + key, "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode("utf-8"))
        infos = data.get("balance_infos") or []
        if infos:
            return {"status": "ok", "text": _fmt_money(infos[0])}
        return {"status": "error", "text": "—"}
    except Exception as e:
        _log_exc("balances/deepseek", e)
        return {"status": "error", "text": "查询失败（详见后端日志）"}


def _claude_balance() -> dict:
    """Claude Code status: third-party gateway first, OAuth usage as fallback."""
    try:
        sp = os.path.join(os.path.expanduser("~"), ".claude", "settings.json")
        with open(sp, "r", encoding="utf-8") as fh:
            s = json.load(fh)
        env = s.get("env") or {}
        base = str(env.get("ANTHROPIC_BASE_URL") or "")
        if base:
            model = str(env.get("ANTHROPIC_MODEL") or "已配置")
            if "deepseek.com" in base:
                tok = str(env.get("ANTHROPIC_AUTH_TOKEN") or "")
                if tok:
                    try:
                        import urllib.request
                        req = urllib.request.Request(
                            "https://api.deepseek.com/user/balance",
                            headers={"Authorization": "Bearer " + tok, "Accept": "application/json"},
                        )
                        with urllib.request.urlopen(req, timeout=8) as r:
                            data = json.loads(r.read().decode("utf-8"))
                        infos = data.get("balance_infos") or []
                        if infos:
                            return {"status": "ok", "text": f"{model} · DeepSeek {_fmt_money(infos[0])}"}
                    except Exception:
                        pass
                return {"status": "ok", "text": f"{model} · DeepSeek 官方"}
            name = "千问AI平台" if "qianwenaiapi" in base else "第三方网关"
            return {"status": "ok", "text": f"{model} · {name}"}
    except Exception:
        pass
    p = os.path.join(os.path.expanduser("~"), ".claude", ".credentials.json")
    if not os.path.exists(p):
        return {"status": "login", "text": "未登录 · 登录后可查"}
    try:
        import urllib.request

        with open(p, "r", encoding="utf-8") as fh:
            cred = json.load(fh)
        tok = str(((cred.get("claudeAiOauth") or {}).get("accessToken")) or "")
        if not tok:
            return {"status": "login", "text": "未登录 · 登录后可查"}
        req = urllib.request.Request(
            "https://api.anthropic.com/api/oauth/usage",
            headers={
                "Authorization": "Bearer " + tok,
                "anthropic-beta": "oauth-2025-04-20",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode("utf-8"))

        def used_pct(node: Any) -> Optional[float]:
            try:
                v = float(node.get("utilization") if isinstance(node, dict) else node)
                return v * 100 if v <= 1 else v
            except Exception:
                return None

        fiv = used_pct(data.get("five_hour"))
        sev = used_pct(data.get("seven_day"))
        if fiv is None and sev is None:
            return {"status": "error", "text": "—"}
        parts = []
        if fiv is not None:
            parts.append(f"5小时窗口剩 {max(0, round(100 - fiv))}%")
        if sev is not None:
            parts.append(f"7天剩 {max(0, round(100 - sev))}%")
        return {"status": "ok", "text": " · ".join(parts)}
    except Exception:
        return {"status": "error", "text": "—"}


def _qoder_balance() -> dict:
    """Qoder Credits left, from a hand-read snapshot.

    Qoder has no token-free local usage API — its access token lives encrypted in
    the app's auth.v1.dat — so the number is read from the app/website once and
    cached here. Stale readings fall back to the in-app hint instead of lying."""
    try:
        p = os.path.join(os.path.dirname(_sel_path()), "qoder-balance.json")
        with open(p, "r", encoding="utf-8") as fh:
            d = json.load(fh)
        age = time.time() - float(d.get("read_at") or 0)
        if age > 6 * 3600 or age < -60:
            return {"status": "inapp", "text": "软件内查看·过期"}
        return {"status": "ok", "text": f"剩 {int(d['remaining'])}/{int(d['total'])}"}
    except Exception:
        return {"status": "inapp", "text": "软件内查看"}


def _balances_payload() -> dict:
    now = time.time()
    if _BAL_CACHE["data"] is not None and now - _BAL_CACHE["t"] < _BAL_TTL:
        return _BAL_CACHE["data"]
    with _BAL_LOCK:
        now = time.time()
        if _BAL_CACHE["data"] is not None and now - _BAL_CACHE["t"] < _BAL_TTL:
            return _BAL_CACHE["data"]
        data = {
            "claude-code": _claude_balance(),
            "deepseek-harness": _deepseek_balance(),
            "qoder": _qoder_balance(),
            "trae": {"status": "inapp", "text": "软件内查看"},
            "trae-solo": {"status": "inapp", "text": "软件内查看"},
            "workbuddy": {"status": "local", "text": "本地运行时"},
        }
        _BAL_CACHE["t"] = now
        _BAL_CACHE["data"] = data
    return data


@router.get("/balances")
def balances(refresh: int = Query(0, ge=0, le=1)) -> dict:
    if refresh:
        with _BAL_LOCK:
            _BAL_CACHE["t"] = 0.0
    return {"ok": True, "balances": _balances_payload()}


# --- selection: which software agents are "in the ring" for the next task ----

def _sel_path() -> str:
    try:
        from hermes_constants import get_hermes_home
        base = str(get_hermes_home())
    except Exception:
        base = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "hermes")
    return os.path.join(base, "workbench-graph", "selection.json")


@router.post("/task")
def create_task_ui(payload: dict = Body(...)) -> dict:
    """Field a task from the graph UI: create a kanban card for one agent.

    The gateway dispatcher picks it up on its next tick (~60s)."""
    assignee = str((payload or {}).get("assignee") or "").strip()
    title = str((payload or {}).get("title") or "").strip()[:200]
    body = str((payload or {}).get("body") or "").strip()[:2000] or None
    if not assignee or not title:
        return {"ok": False, "error": "任务负责人与标题必填"}
    if assignee not in _known_assignees():
        return {"ok": False, "error": "未知的任务负责人：" + assignee}
    try:
        from hermes_cli import kanban_db as kb
        from hermes_cli import kanban_db_connect as kbc
        with kbc.connect_closing() as conn:
            tid = kb.create_task(conn, title=title, body=body, assignee=assignee, created_by="workbench-ui")
            try:
                conn.commit()
            except Exception:
                pass
        return {"ok": True, "task_id": tid}
    except Exception as e:
        _log_exc("task/create", e)
        return {"ok": False, "error": "建卡失败，请查看后端日志"}


# --- builtin-models: read/adjust each SOFTWARE's own model choice -------------
# The model belongs to the software (its built-in setting); the workbench only
# exposes the knob. claude-code -> its settings.json env; deepseek-harness ->
# its headless profile patch; GUI apps -> picked inside the app.

_CC_MODELS = ["deepseek-flash[1m]", "deepseek-flash", "deepseek-v4-pro"]
_DSH_MODELS = ["deepseek-flash", "deepseek-v4-pro"]
_QODER_SETTINGS = os.path.join(os.path.expanduser("~"), ".qoder-cn", "settings.json")
_QODER_MODELS = ["Auto", "Qwen3.8-Max", "Qwen3.8-Flash", "Qwen3.7-Max", "Qwen3.7-Plus", "Qwen3.7-Flash",
                 "DeepSeek-V4-Pro", "DeepSeek-Flash", "GLM-5.3", "GLM-5.3-Flash", "GLM-5.2",
                 "Kimi-K3", "Kimi-K2.8-Preview", "MiniMax-M2.7",
                 "Qwen-3.8-Flash", "Qwen-3.8-Max"]  # full-capability account entries (2026-10-10)
_QODER_UUID_MAP = {"Qwen-3.8-Flash": "7bc3660e-5bb8-47ff-8979-f49fc5444edc",
                   "Qwen-3.8-Max": "d6eaa6a3-0299-4c3b-80e4-4001434309e4"}  # settings.json model.name must carry the bare UUID
_QODER_UUID_REV = {v: k for k, v in _QODER_UUID_MAP.items()}
_CB_SETTINGS = os.path.join(os.path.expanduser("~"), ".codebuddy", "settings.json")
_CB_MODELS = ["step-5-preview", "hy4-preview-f", "hy3", "hy3-x", "space-bunny",
              "deepseek-v4.1-flash", "deepseek-v4-pro", "glm-5.3", "glm-5.3-flash", "glm-5.2",
              "glm-5.1", "glm-5v-turbo", "kimi-k3-1", "kimi-k2.8-preview", "kimi-k2.7", "kimi-k2.6",
              "minimax-m3", "minimax-m2.7", "hy4-preview", "hy4-preview-x", "auto"]
# 2026-10-12: synced to `codebuddy --help` supported list (step-5-preview/space-bunny/minimax-m2.7/kimi-k2.6 added);
# 前三个 = 限免 credit x0.00（step-5-preview 免费窗 10-12→10-25、hy4-preview-f 14 天试用、hy3 每日赠送至 10-31），其余计费。
_DSH_PATCH_HEADER = (
    "# Your patch layer for this dsh profile, applied after every bundle layer:\n"
    "# a top-level YAML array of loader patch entries (id-targeted config\n"
    "# overrides, disables, and insert lists; `!!js` expressions allowed).\n"
)


# --- trae: built-in model lives in the Trae CN state store (state.vscdb) -------

def _trae_state_db() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "Trae CN", "User", "globalStorage", "state.vscdb")


def _trae_load() -> dict:
    """Read the Trae state tables (model catalog + selections). Raises on failure."""
    import sqlite3
    db = _trae_state_db()
    con = sqlite3.connect(db)
    try:
        rows = dict(con.execute("select key, value from ItemTable").fetchall())
    finally:
        con.close()
    uid = ""
    for k in rows:
        m = re.match(r"^(\d+)[_:]AI\.agent\.model", str(k))
        if m:
            uid = m.group(1)
            break
    if not uid:
        raise ValueError("trae uid not found in state.vscdb")

    def _load(key):
        v = rows.get(key)
        if not v:
            return None
        sv = v.decode("utf-8", "replace") if isinstance(v, (bytes, bytearray)) else str(v)
        return json.loads(sv)

    lists = {}
    for mk in (uid + "_AI.agent.model.model_list_map", uid + ":AI.agent.model.model_list_map"):
        for label, lst in (_load(mk) or {}).items():
            tgt = lists.setdefault(label, {})
            for m in lst or []:
                nm = str(m.get("name") or "")
                if nm:
                    tgt[nm] = m
    return {"db": db, "lists": lists,
            "recent": _load(uid + ":AI.agent.model.recent_user_selection_by_agent_label") or {},
            "recent_key": uid + ":AI.agent.model.recent_user_selection_by_agent_label",
            "sess": _load(uid + ":AI.agent.model.session_selected_model") or {},
            "sess_key": uid + ":AI.agent.model.session_selected_model",
            "gmap": _load(uid + "_ai-chat:sessionRelation:globalModelMap") or {},
            "gmap_key": uid + "_ai-chat:sessionRelation:globalModelMap"}


_TRAE_LABEL_LIST = {"agent": "builder", "solo_agent": "solo_agent"}
_TRAE_MID_RE = re.compile(r"^[a-z_]+_1__(.+)_null$")


def _trae_name_from_mid(mid: str) -> str:
    m = _TRAE_MID_RE.match(str(mid or ""))
    return m.group(1) if m else ""


def _trae_options(st: dict) -> list:
    names = []
    for label in ("builder", "builder_v3", "chat_v3", "solo_agent"):
        for nm, mm in (st["lists"].get(label) or {}).items():
            if mm.get("provider"):  # custom / external providers excluded
                continue
            if nm not in names:
                names.append(nm)
    return names


def _trae_current(st: dict) -> str:
    # the chat-window model pill is driven by ai-chat sessionRelation globalModelMap
    gm = str((st.get("gmap") or {}).get("solo_coder") or "")
    if gm.startswith("1_-_"):
        return gm[4:]
    for entry in (st["sess"] or {}).values():
        for label in ("agent", "solo_agent"):
            nm = _trae_name_from_mid(((entry or {}).get(label) or {}).get("modelId"))
            if nm:
                return nm
    for label in ("solo_agent", "agent"):
        nm = _trae_name_from_mid((st["recent"].get(label) or {}).get("modelId"))
        if nm:
            return nm
    return "Doubao-Seed-Code"


def _trae_builtin_payload() -> dict:
    try:
        st = _trae_load()
        return {"current": _trae_current(st), "editable": True,
                "where": "Trae 状态库（重启 Trae 后生效）", "options": _trae_options(st)}
    except Exception:
        return {"current": "在软件内选择", "editable": False, "where": "软件内", "options": []}


def _is_trae_running() -> bool:
    """Trae 图形界面是否在运行（写它的状态库前必须关闭，否则写入会被覆盖）。"""
    try:
        import subprocess
        kw = {"capture_output": True, "text": True, "timeout": 15}
        if os.name == "nt":
            kw["creationflags"] = subprocess.CREATE_NO_WINDOW
        for name in ("Trae CN.exe", "Trae.exe"):
            r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq " + name], **kw)
            if name.lower() in (r.stdout or "").lower():
                return True
        return False
    except Exception:
        return False


def _trae_set_model(model: str) -> dict:
    """Write the chosen built-in model into Trae's state store, for every selection
    label the model is valid for. Close Trae first for the write to stick."""
    import sqlite3
    if _is_trae_running():
        return {"ok": False, "error": "Trae 正在运行：请先关闭 Trae 再切换（运行中写入会被覆盖）"}
    st = _trae_load()
    if model not in _trae_options(st):
        return {"ok": False, "error": "不支持的模型名（Trae 内置模型列表）"}
    changed = []
    for label, catalog in _TRAE_LABEL_LIST.items():
        if model not in (st["lists"].get(catalog) or {}):
            continue
        cur = st["recent"].get(label) or {}
        mode = cur.get("mode", 1 if label == "agent" else 0)
        st["recent"][label] = {"modelId": "%s_1__%s_null" % (label, model), "mode": mode}
        changed.append(label)
    if not changed:
        return {"ok": False, "error": "该模型不在 Trae 可选清单内"}
    for entry in (st["sess"] or {}).values():
        for label, catalog in _TRAE_LABEL_LIST.items():
            if label in (entry or {}) and model in (st["lists"].get(catalog) or {}):
                mode = (entry[label] or {}).get("mode", 1 if label == "agent" else 0)
                entry[label] = {"modelId": "%s_1__%s_null" % (label, model), "mode": mode}
    con = sqlite3.connect(st["db"])
    try:
        gm = dict(st.get("gmap") or {})
        gm["solo_coder"] = "1_-_" + model
        con.execute("update ItemTable set value=? where key=?",
                    (json.dumps(gm, ensure_ascii=False, separators=(",", ":")), st["gmap_key"]))
        con.execute("update ItemTable set value=? where key=?",
                    (json.dumps(st["recent"], ensure_ascii=False, separators=(",", ":")), st["recent_key"]))
        con.execute("update ItemTable set value=? where key=?",
                    (json.dumps(st["sess"], ensure_ascii=False, separators=(",", ":")), st["sess_key"]))
        con.commit()
    finally:
        con.close()
    _trae_patch_workspaces(model, st["db"])
    return {"ok": True, "agent": "trae", "model": model, "labels": changed}


def _trae_patch_workspaces(model: str, db: str) -> None:
    """Best-effort: update per-workspace sessionRelation model maps too."""
    import glob as _glob
    base = os.path.dirname(os.path.dirname(db))  # .../Trae CN/User
    val = "1_-_" + model
    for wdb in _glob.glob(os.path.join(base, "workspaceStorage", "*", "state.vscdb")):
        try:
            wc = sqlite3.connect(wdb)
            try:
                for k, in list(wc.execute("select key from ItemTable where key like '%:sessionRelation:globalModelMap'")):
                    row = wc.execute("select value from ItemTable where key=?", (k,)).fetchone()
                    d = json.loads(row[0]) if row and row[0] else {}
                    if isinstance(d, dict):
                        d["solo_coder"] = val
                        wc.execute("update ItemTable set value=? where key=?",
                                   (json.dumps(d, ensure_ascii=False, separators=(",", ":")), k))
                for k, in list(wc.execute("select key from ItemTable where key like '%:sessionRelation:modelMap'")):
                    row = wc.execute("select value from ItemTable where key=?", (k,)).fetchone()
                    d = json.loads(row[0]) if row and row[0] else {}
                    if isinstance(d, dict):
                        for _sid, m in list(d.items()):
                            if isinstance(m, dict) and "solo_coder" in m:
                                m["solo_coder"] = val
                        wc.execute("update ItemTable set value=? where key=?",
                                   (json.dumps(d, ensure_ascii=False, separators=(",", ":")), k))
                wc.commit()
            finally:
                wc.close()
        except Exception:
            pass


def _cc_settings_path() -> str:
    return os.path.join(os.path.expanduser("~"), ".claude", "settings.json")


def _dsh_patch_path(profile: str = "headless") -> str:
    return os.path.join(os.path.expanduser("~"), ".dsh", "profiles", profile, "cordis.patch.yml")


def _dsh_model_from_patch(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            txt = fh.read()
        m = re.search(r"agent-default-model[\s\S]{0,400}?model:\s*([\w.\-]+)", txt)
        return m.group(1) if m else ""
    except Exception:
        return ""


# --- 一键更新：从各软件自身的权威来源重新抓取内置模型清单 -----------------------
# 目录文件 model-catalog.json（与后端同目录）由 POST /refresh-models 原子写入，
# 一旦存在即以它为准；抓取失败时不覆盖旧值。来源：Claude Code=其端点 /v1/models、
# Harness=主配置端点 /v1/models、Qoder=`qoderclicn --list-models`、CodeBuddy=`codebuddy --help`。

_CATALOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model-catalog.json")


def _load_catalog() -> dict:
    try:
        with open(_CATALOG_PATH, "r", encoding="utf-8") as fh:
            c = json.load(fh)
        return c if isinstance(c, dict) else {}
    except Exception:
        return {}


def _catalog_options(agent: str, default: list) -> list:
    entry = _load_catalog().get(agent) or {}
    opts = entry.get("options")
    if isinstance(opts, list) and opts and all(isinstance(x, str) and x for x in opts):
        return list(opts)
    return list(default)


def _cat_stamp(agent: str) -> dict:
    entry = _load_catalog().get(agent) or {}
    out = {}
    if entry.get("updated_at"):
        out["updated_at"] = entry["updated_at"]
    if entry.get("source"):
        out["source"] = entry["source"]
    return out


def _iso_now() -> str:
    return time.strftime("%Y-%m-%d %H:%M")


def _paged_ids(url_base: str, headers: dict) -> list:
    """GET a /models endpoint (OpenAI/Anthropic shape); follows Anthropic has_more pages."""
    import urllib.request
    out, url = [], url_base
    for _ in range(6):
        req = urllib.request.Request(url, method="GET")
        for k, v in headers.items():
            req.add_header(k, v)
        with urllib.request.urlopen(req, timeout=20) as r:
            j = json.loads(r.read().decode("utf-8", "replace"))
        data = j.get("data") if isinstance(j, dict) else None
        if not isinstance(data, list):
            data = (j.get("models") if isinstance(j, dict) else None) or []
        for m in data:
            mid = m.get("id") if isinstance(m, dict) else m
            if mid and str(mid) not in out:
                out.append(str(mid))
        if not (isinstance(j, dict) and j.get("has_more") and j.get("last_id")):
            break
        url = url_base + "&after_id=" + str(j["last_id"])
    return out


def _main_cfg_model_block() -> dict:
    """base_url/api_key of the main hermes config `model:` block (regex; no YAML dependency)."""
    p = os.path.join(os.environ.get("LOCALAPPDATA", ""), "hermes", "config.yaml")
    try:
        with open(p, "r", encoding="utf-8") as fh:
            txt = fh.read()
    except Exception:
        return {}
    m = re.search(r"(?ms)^model:\s*\n((?:[ \t]+[^\n]*\n)+)", txt)
    if not m:
        return {}
    blk = m.group(1)
    out = {}
    for k in ("base_url", "api_key"):
        mm = re.search(r"^\s+" + k + r":\s*(\S+)\s*$", blk, re.M)
        if mm:
            out[k] = mm.group(1).strip().strip("\"'")
    return out


def _run_quiet(args: list, timeout: int = 60):
    import subprocess
    kw = {}
    if os.name == "nt":
        kw["creationflags"] = subprocess.CREATE_NO_WINDOW
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, **kw)


def _disc_cc() -> dict:
    with open(_cc_settings_path(), "r", encoding="utf-8") as fh:
        env = json.load(fh).get("env") or {}
    base = str(env.get("ANTHROPIC_BASE_URL") or "").rstrip("/")
    tok = str(env.get("ANTHROPIC_AUTH_TOKEN") or "")
    if not base or not tok:
        return {"ok": False, "error": "settings.json 缺 ANTHROPIC_BASE_URL/AUTH_TOKEN"}
    opts = _paged_ids(base + "/v1/models?limit=200", {"x-api-key": tok})
    if not opts:
        return {"ok": False, "error": "端点未返回模型列表"}
    return {"ok": True, "options": opts, "source": base.split("//")[-1].split("/")[0] + " /v1/models"}


def _disc_dsh() -> dict:
    blk = _main_cfg_model_block()
    base = str(blk.get("base_url") or "").rstrip("/")
    key = str(blk.get("api_key") or "")
    if not base or not key:
        return {"ok": False, "error": "主配置缺 model.base_url/api_key"}
    opts = _paged_ids(base + "/models", {"Authorization": "Bearer " + key})
    if not opts:
        return {"ok": False, "error": "端点未返回模型列表"}
    return {"ok": True, "options": opts, "source": base.split("//")[-1].split("/")[0] + " /v1/models"}


def _disc_qoder() -> dict:
    exe = os.path.join(os.path.expanduser("~"), ".qodersec", "bin", "qoderclicn.exe")
    if not os.path.exists(exe):
        return {"ok": False, "error": "qoderclicn.exe 未找到"}
    r = _run_quiet([exe, "--list-models"], timeout=90)
    opts = []
    for ln in (r.stdout or "").splitlines():
        ln = ln.strip()
        if not ln or ln.upper() == "MODEL":
            continue
        nm = re.sub(r"\s*\([0-9a-fA-F-]{36}\)\s*$", "", ln).strip()
        if nm and nm not in opts:
            opts.append(nm)
    if not opts:
        return {"ok": False, "error": "未解析到模型（未登录？）"}
    return {"ok": True, "options": opts, "source": "qoderclicn --list-models"}


def _disc_workbuddy() -> dict:
    exe = os.path.join(os.environ.get("LOCALAPPDATA", ""), "codebuddy", "bin", "codebuddy.exe")
    if not os.path.exists(exe):
        return {"ok": False, "error": "codebuddy.exe 未找到"}
    r = _run_quiet([exe, "--help"], timeout=60)
    m = re.search(r"Currently supported:\s*\(([^)]+)\)", (r.stdout or "") + "\n" + (r.stderr or ""))
    if not m:
        return {"ok": False, "error": "codebuddy --help 未列出模型清单"}
    opts = []
    for x in m.group(1).split(","):
        x = x.strip()
        if x and x not in opts:
            opts.append(x)
    if "auto" not in opts:
        opts.append("auto")  # 产品层 Auto 入口；CLI 清单未列
    return {"ok": True, "options": opts, "source": "codebuddy --help"}


def _refresh_models_impl() -> dict:
    cat = _load_catalog()
    results = {}
    for agent, default, fn in (
        ("claude-code", _CC_MODELS, _disc_cc),
        ("deepseek-harness", _DSH_MODELS, _disc_dsh),
        ("qoder", _QODER_MODELS, _disc_qoder),
        ("workbuddy", _CB_MODELS, _disc_workbuddy),
    ):
        try:
            r = fn()
        except Exception as e:
            _log_exc("refresh-models/" + agent, e)
            r = {"ok": False, "error": "抓取失败（详见后端日志）"}
        if r.get("ok"):
            old = _catalog_options(agent, default)
            r["added"] = [m for m in r["options"] if m not in old]
            r["removed"] = [m for m in old if m not in r["options"]]
            cat[agent] = {"options": r["options"], "source": r.get("source", ""), "updated_at": _iso_now()}
        results[agent] = r
    try:
        st = _trae_load()
        results["trae"] = {"ok": True, "options": _trae_options(st), "source": "Trae 状态库（本就实时）",
                           "added": [], "removed": []}
    except Exception as e:
        _log_exc("refresh-models/trae", e)
        results["trae"] = {"ok": False, "error": "抓取失败（详见后端日志）"}
    try:
        tmp = _CATALOG_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(cat, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        os.replace(tmp, _CATALOG_PATH)
        saved = True
    except Exception as e:
        saved = False
        _log_exc("refresh-models/save", e)
        results["_save"] = {"ok": False, "error": "写入失败（详见后端日志）"}
    return {"ok": True, "saved": saved, "results": results}


@router.post("/refresh-models")
def refresh_models() -> dict:
    """一键更新：同步各软件内置模型清单（幂等，可反复点）。"""
    return _refresh_models_impl()


def _builtin_models_payload() -> dict:
    out = {}
    cur = ""
    try:
        with open(_cc_settings_path(), "r", encoding="utf-8") as fh:
            env = (json.load(fh).get("env") or {})
        cur = str(env.get("ANTHROPIC_MODEL") or "")
    except Exception:
        pass
    out["claude-code"] = {"current": cur or "—", "editable": True, "where": "Claude Code 设置",
                          "options": _catalog_options("claude-code", _CC_MODELS), **_cat_stamp("claude-code")}
    cur = _dsh_model_from_patch(_dsh_patch_path("headless")) or _dsh_model_from_patch(_dsh_patch_path("desktop"))
    out["deepseek-harness"] = {"current": cur or "（软件默认）", "editable": True, "where": "Harness 配置",
                               "options": _catalog_options("deepseek-harness", _DSH_MODELS), **_cat_stamp("deepseek-harness")}
    cur = ""
    try:
        with open(_QODER_SETTINGS, "r", encoding="utf-8") as fh:
            _mv = (json.load(fh) or {}).get("model")
        cur = str(((_mv.get("name") if isinstance(_mv, dict) else _mv) or ""))
        cur = _QODER_UUID_REV.get(cur, cur)
    except Exception:
        pass
    out["qoder"] = {"current": cur or "自动", "editable": True, "where": "Qoder 设置",
                    "options": _catalog_options("qoder", _QODER_MODELS), **_cat_stamp("qoder")}
    cur = ""
    try:
        with open(_CB_SETTINGS, "r", encoding="utf-8") as fh:
            cur = str((json.load(fh) or {}).get("model") or "")
    except Exception:
        pass
    out["workbuddy"] = {"current": cur or "自动", "editable": True, "where": "CodeBuddy 设置",
                        "options": _catalog_options("workbuddy", _CB_MODELS), **_cat_stamp("workbuddy")}
    out["trae"] = _trae_builtin_payload()
    out["trae-solo"] = {"current": "在软件内选择", "editable": False, "where": "软件内", "options": []}
    return out


@router.get("/builtin-models")
def builtin_models() -> dict:
    return {"ok": True, "models": _builtin_models_payload()}


@router.post("/builtin-model")
def set_builtin_model(payload: dict = Body(...)) -> dict:
    agent = str((payload or {}).get("agent") or "").strip()
    model = str((payload or {}).get("model") or "").strip()
    if not agent or not model:
        return {"ok": False, "error": "软件与模型名必填"}
    if not re.match(r"^[A-Za-z0-9._\-\[\]]+$", model):
        return {"ok": False, "error": "模型名含非法字符"}
    if agent == "claude-code":
        if model not in _catalog_options("claude-code", _CC_MODELS):
            return {"ok": False, "error": "不支持的模型名（可点「更新清单」同步后再试）"}
        path = _cc_settings_path()
        try:
            with open(path, "r", encoding="utf-8") as fh:
                d = json.load(fh)
            env = d.setdefault("env", {})
            for k in ("ANTHROPIC_MODEL", "ANTHROPIC_DEFAULT_OPUS_MODEL", "ANTHROPIC_DEFAULT_SONNET_MODEL",
                      "ANTHROPIC_DEFAULT_HAIKU_MODEL", "ANTHROPIC_SMALL_FAST_MODEL", "CLAUDE_CODE_SUBAGENT_MODEL"):
                env[k] = model
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(d, fh, ensure_ascii=False, indent=2)
                fh.write("\n")
            os.replace(tmp, path)
            return {"ok": True, "agent": agent, "model": model}
        except Exception as e:
            _log_exc("builtin-model", e)
            return {"ok": False, "error": "切换失败，请查看后端日志"}
    if agent == "deepseek-harness":
        path = _dsh_patch_path("headless")
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            old = ""
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as fh:
                    old = fh.read()
            m = re.search(r"- id: agent-default-model\n(?:[ \t]+[^\n]*\n|\n)*", old)
            if m:
                old = old[:m.start()] + old[m.end():]
            old = re.sub(r"^\[\]\s*$", "", old, flags=re.M).strip("\n")
            entry = ("- id: agent-default-model\n"
                     "  name: \"@deepseek-ai/dsh-agent-default-model\"\n"
                     "  config:\n"
                     "    provider: deepseek-official\n"
                     f"    model: {model}\n"
                     "    reasoningEffort: high\n")
            body = (old + "\n\n" if old else _DSH_PATCH_HEADER) + entry
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                fh.write(body)
            os.replace(tmp, path)
            return {"ok": True, "agent": agent, "model": model}
        except Exception as e:
            _log_exc("builtin-model", e)
            return {"ok": False, "error": "切换失败，请查看后端日志"}
    if agent == "qoder":
        if model not in _catalog_options("qoder", _QODER_MODELS):
            return {"ok": False, "error": "不支持的模型名（以 --list-models 显示名为准）"}
        model = _QODER_UUID_MAP.get(model, model)
        path = _QODER_SETTINGS
        try:
            d = {}
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as fh:
                    d = json.load(fh) or {}
            mv = d.get("model")
            if not isinstance(mv, dict):
                mv = {}
            mv["name"] = model
            if model == _QODER_UUID_MAP.get("Qwen-3.8-Flash") or model == _QODER_UUID_MAP.get("Qwen-3.8-Max"):
                prefs = mv.setdefault("preferences", {})
                prefs.setdefault(model, {"contextWindow": 1000000, "reasoning": {"effort": "max"}})
            d["model"] = mv
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(d, fh, ensure_ascii=False, indent=2)
                fh.write("\n")
            os.replace(tmp, path)
            return {"ok": True, "agent": agent, "model": model}
        except Exception as e:
            _log_exc("builtin-model", e)
            return {"ok": False, "error": "切换失败，请查看后端日志"}
    if agent == "workbuddy":
        if model not in _catalog_options("workbuddy", _CB_MODELS):
            return {"ok": False, "error": "不支持的模型名（CodeBuddy 云端模型列表）"}
        path = _CB_SETTINGS
        try:
            d = {}
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as fh:
                    d = json.load(fh) or {}
            d["model"] = model
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(d, fh, ensure_ascii=False, indent=2)
                fh.write("\n")
            os.replace(tmp, path)
            return {"ok": True, "agent": agent, "model": model}
        except Exception as e:
            _log_exc("builtin-model", e)
            return {"ok": False, "error": "切换失败，请查看后端日志"}
    if agent == "trae":
        try:
            return _trae_set_model(model)
        except Exception as e:
            _log_exc("builtin-model", e)
            return {"ok": False, "error": "切换失败，请查看后端日志"}
    return {"ok": False, "error": "该软件不支持远程调模型，请在软件内选择"}


# --- wake: launch a GUI software agent's app (explicit request only) ----------

_WAKE_TARGETS = {
    "qoder": (r"%LOCALAPPDATA%\Qoder CN\Qoder CN Launcher\Qoder CN Launcher.exe", True),
    "trae": (r"%USERPROFILE%\Desktop\Trae CN\bin\trae-cn.cmd", True),
    "trae-solo": (r"%USERPROFILE%\Desktop\TRAE SOLO CN\bin\trae-solo-cn.cmd", True),
    "workbuddy": (r"%LOCALAPPDATA%\Programs\WorkBuddy\WorkBuddy.exe", False),
}


@router.post("/wake")
def wake(payload: dict = Body(...)) -> dict:
    """Open a GUI agent's app (optionally at a workspace path). Headless agents
    are woken by the dispatcher itself — nothing to launch for them."""
    agent = str((payload or {}).get("agent") or "").strip()
    path = str((payload or {}).get("path") or "").strip()
    if agent in ("claude-code", "deepseek-harness"):
        return {"ok": True, "note": "无头通道：派发即唤醒，无需打开界面"}
    tgt = _WAKE_TARGETS.get(agent)
    if not tgt:
        return {"ok": False, "error": "未知的软件智能体"}
    exe = os.path.expandvars(tgt[0])
    if not os.path.exists(exe):
        return {"ok": False, "error": "找不到启动程序：" + exe}
    try:
        import subprocess
        args = [exe]
        if tgt[1] and path:
            p = os.path.expandvars(path)
            if len(p) > 260 or not os.path.isabs(p) or not os.path.isdir(p):
                return {"ok": False, "error": "路径无效：需为存在的绝对目录"}
            args.append(os.path.normpath(p))
        flags = 0
        if os.name == "nt":
            flags = subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, "DETACHED_PROCESS", 0)
        subprocess.Popen(args, creationflags=flags, close_fds=True)
        return {"ok": True, "launched": exe}
    except Exception as e:
        _log_exc("wake", e)
        return {"ok": False, "error": "启动失败，请查看后端日志"}


# --- instructions: the self-config pack pasted into each software app ---------

@router.get("/instructions")
def instructions() -> dict:
    try:
        path = os.path.join(os.path.dirname(_sel_path()), "agent-setup.md")
        with open(path, "r", encoding="utf-8") as fh:
            return {"ok": True, "text": fh.read()}
    except Exception:
        return {"ok": False, "text": ""}


@router.get("/selection")
def get_selection() -> dict:
    try:
        with open(_sel_path(), "r", encoding="utf-8") as fh:
            data = json.load(fh)
        agents = data.get("agents") if isinstance(data, dict) else data
        return {"ok": True, "agents": [str(a) for a in (agents or [])]}
    except Exception:
        return {"ok": True, "agents": []}


@router.post("/selection")
def set_selection(payload: dict = Body(...)) -> dict:
    agents = payload.get("agents") if isinstance(payload, dict) else None
    if not isinstance(agents, list):
        return {"ok": False, "error": "agents 需为数组"}
    known = {e[0] for e in _EXTERNALS}
    clean, seen = [], set()
    for a in agents:
        s = str(a)
        if s in known and s not in seen:
            seen.add(s)
            clean.append(s)
    if len(clean) > 16:
        return {"ok": False, "error": "最多支持 16 个智能体"}
    path = _sel_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"agents": clean, "updated_at": time.time()}, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, path)
    return {"ok": True, "agents": clean}
