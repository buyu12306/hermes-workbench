#!/usr/bin/env python
"""WorkBuddy 免费模型额度守护 (free-model quota guard).

限免三模型（credit x0.00，2026-10-12 产品配置实况）：
  step-5-preview  限时免费 10-12 → 10-25（官方合作窗，1M ctx）
  hy4-preview-f   14 天试用（自启用起算，960K ctx）
  hy3             每日赠送免费额度至 10-31（192K ctx）
其余模型按 credits 计费（x0.04–x2.20），不要碰。

命令：
  status           经本地网关探测三个限免模型 + 显示 worker/引擎当前模型与最近切换记录
  guard [--dry]    当前模型（限免范围内）被判定不可用时，自动切到下一个可用限免模型
                   worker → profiles/workbuddy/config.yaml model.default（经 hermes config set 写）
                   引擎   → ~/.codebuddy/settings.json model（原子写，备份一次）
                   v2：只对"额度类"失败切换（非额度失败需连续 2 次才算数）；免费窗
                   已过期/未开启的模型不再被切入，且正在使用的过期模型会被挪到窗内模型；
                   exit 0=正常 / 3=网关不可达 / 2=全不可用或存在过期
  pick             打印第一个可用的限免模型 id（供派卡 --model 取值；exit 1 = 全不可用）
  restore          把 worker/引擎回切到 guard 切换前的模型（记录于状态文件；失败 exit 2）

探测经本地网关 127.0.0.1:8787（同一腾讯账号），失败会重试 1 次以免误判瞬时抖动。
运行： .venv/Scripts/python.exe .build/workbench/73-wb-quota.py status
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

from ruamel.yaml import YAML

HOME = os.environ["LOCALAPPDATA"].replace("\\", "/") + "/hermes"
REPO = os.environ["USERPROFILE"].replace("\\", "/") + "/Desktop/hermes-agent-main"
GATEWAY = "http://127.0.0.1:8787/v1"
AUTH = "Bearer codebuddy-local"
FREE_ORDER = ["step-5-preview", "hy4-preview-f", "hy3"]
FREE_NOTES = {
    "step-5-preview": "免费窗 10-12→10-25, 1M",
    "hy4-preview-f": "14天试用, 960K",
    "hy3": "每日免费至 10-31, 192K",
}
WORKER_CFG = f"{HOME}/profiles/workbuddy/config.yaml"
ENGINE_SETTINGS = os.path.expanduser("~").replace("\\", "/") + "/.codebuddy/settings.json"
HERMES_EXE = f"{REPO}/.venv/Scripts/hermes.exe"
CODEBUDDY_EXE = os.environ["LOCALAPPDATA"].replace("\\", "/") + "/codebuddy/bin/codebuddy.exe"
LOG = f"{HOME}/codebuddy-gateway/quota-guard.log"
PROBE_TIMEOUT = 75

QUOTA_MARKERS = re.compile(
    r"6004|6005|14018|额度|allowance|insufficient|not enough|exceed|credit|rate.?limit|429|too many",
    re.I,
)

# 限免窗口（结构化；过期即排除，R73-2）：(起, 止, 备注)
FREE_WINDOWS = {
    "step-5-preview": ("2026-10-12", "2026-10-25", "限时免费（官方合作窗）"),
    "hy4-preview-f": ("2026-10-12", "2026-10-31", "14 天试用（自启用起算）"),
    "hy3": ("2026-10-12", "2026-10-31", "每日赠送免费额度"),
}
STATE_FILE = f"{HOME}/codebuddy-gateway/quota-guard-state.json"


def free_now() -> tuple[list[str], list[str]]:
    """(窗口内, 已过期/未开启) —— 只对窗口内的模型做切换决策。"""
    today = dt.date.today().isoformat()
    kept, expired = [], []
    for m in FREE_ORDER:
        start, end, _note = FREE_WINDOWS.get(m, (None, None, None))
        if start and end and start <= today <= end:
            kept.append(m)
        else:
            expired.append(m)
    return kept, expired


def _state_load() -> dict:
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh) or {}
    except Exception:
        return {}


def _state_save(st: dict) -> None:
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        tmp = STATE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(st, fh, ensure_ascii=False)
        os.replace(tmp, STATE_FILE)
    except Exception:
        pass


def _bump_soft_fail(layer: str, model: str) -> int:
    st = _state_load()
    d = st.setdefault("soft_fails", {})
    key = f"{layer}:{model}"
    d[key] = int(d.get(key, 0)) + 1
    _state_save(st)
    return d[key]


def _reset_soft_fail(layer: str, model: str) -> None:
    st = _state_load()
    d = st.get("soft_fails") or {}
    if d.pop(f"{layer}:{model}", None) is not None:
        _state_save(st)


def _remember_prev(layer: str, model: str) -> None:
    st = _state_load()
    st.setdefault("prev", {})[layer] = model
    _state_save(st)


def now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def log_event(rec: dict) -> None:
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    rec = {"ts": now_iso(), **rec}
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def http_json(method: str, url: str, body: dict | None = None, timeout: int = PROBE_TIMEOUT):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", AUTH)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, raw
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # connection/timeout
        return None, f"{type(e).__name__}: {e}"


def gateway_up() -> bool:
    st, raw = http_json("GET", f"{GATEWAY}/models", timeout=6)
    return st == 200


def probe(model: str, attempts: int = 2) -> dict:
    """One cheap round-trip through the gateway. ok=True means the model answered without error."""
    last = {}
    for i in range(attempts):
        t0 = time.time()
        st, raw = http_json("POST", f"{GATEWAY}/chat/completions", {
            "model": model,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 16,
            "stream": False,
        })
        ms = int((time.time() - t0) * 1000)
        ok = False
        detail = ""
        if st == 200:
            try:
                j = json.loads(raw)
                if not (isinstance(j, dict) and j.get("error")):
                    ok = True
                else:
                    detail = str(j.get("error"))[:220]
            except Exception:
                detail = "unparseable body: " + raw[:160]
        else:
            detail = f"http {st}: {raw[:200]}" if raw else f"http {st}"
        if ok:
            return {"ok": True, "ms": ms, "detail": ""}
        last = {"ok": False, "ms": ms, "detail": detail,
                "quota_like": bool(QUOTA_MARKERS.search(detail)) if detail else False}
        if i < attempts - 1:
            time.sleep(3)
    return last


def read_worker_model() -> str:
    y = YAML(typ="safe")
    with open(WORKER_CFG, "r", encoding="utf-8") as fh:
        cfg = y.load(fh) or {}
    return str(((cfg.get("model") or {}).get("default")) or "")


def write_worker_model(model: str) -> tuple[bool, str]:
    # backup once, then the sanctioned hermes writer
    bak = WORKER_CFG + ".bak-quotaguard"
    if not os.path.exists(bak):
        shutil.copy2(WORKER_CFG, bak)
    try:
        r = subprocess.run([HERMES_EXE, "-p", "workbuddy", "config", "set", "model.default", model],
                           capture_output=True, text=True, timeout=90, cwd=REPO)
        out = (r.stdout or "") + (r.stderr or "")
        if r.returncode != 0:
            return False, f"hermes exit {r.returncode}: {out.strip()[:200]}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"
    got = read_worker_model()
    return (got == model), f"readback={got}"


def read_engine_model() -> str:
    try:
        with open(ENGINE_SETTINGS, "r", encoding="utf-8") as fh:
            return str((json.load(fh) or {}).get("model") or "")
    except Exception:
        return ""


def write_engine_model(model: str) -> tuple[bool, str]:
    """Prefer the CLI's own writer (`codebuddy config set -g model <m>`); fall back to a direct,
    atomic JSON edit that preserves every other key (incl. the gateway password)."""
    try:
        subprocess.run([CODEBUDDY_EXE, "config", "set", "-g", "model", model],
                       capture_output=True, text=True, timeout=120)
        if read_engine_model() == model:
            return True, "via codebuddy config set -g"
    except Exception:
        pass
    bak = ENGINE_SETTINGS + ".bak-quotaguard"
    try:
        with open(ENGINE_SETTINGS, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not os.path.exists(bak):
            shutil.copy2(ENGINE_SETTINGS, bak)
        data["model"] = model
        tmp = ENGINE_SETTINGS + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\r\n") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        os.replace(tmp, ENGINE_SETTINGS)
        got = read_engine_model()
        return (got == model), f"direct-json fallback: readback={got}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def tail_log(n: int = 6) -> list[dict]:
    try:
        with open(LOG, "r", encoding="utf-8") as fh:
            lines = fh.readlines()[-n:]
        return [json.loads(x) for x in lines if x.strip()]
    except Exception:
        return []


def collect_status() -> dict:
    up = gateway_up()
    probes = {}
    for m in FREE_ORDER:
        probes[m] = probe(m) if up else {"ok": False, "ms": 0, "detail": "gateway down"}
    return {
        "gateway_up": up,
        "probes": probes,
        "worker_model": read_worker_model(),
        "engine_model": read_engine_model(),
        "recent_log": tail_log(6),
    }


def cmd_status(args) -> int:
    st = collect_status()
    if args.json:
        print(json.dumps(st, ensure_ascii=False, indent=2))
        return 0
    print("== WorkBuddy 限免模型额度守护 (status) ==")
    print(f"gateway {GATEWAY}: {'UP' if st['gateway_up'] else 'DOWN ⚠ (检查 supervisor / 83-gateway-relaunch.ps1)'}")
    kept, expired = free_now()
    print("探测（经网关，同账号）：")
    for m in FREE_ORDER:
        p = st["probes"][m]
        mark = "OK " if p["ok"] else "FAIL"
        extra = f"  {p.get('detail','')[:90]}" if not p["ok"] else ""
        win = "" if m in kept else "  ⚠已过期/未开启(不参与切换)"
        print(f"  {m:<16} {mark}  {p['ms']:>6}ms  [{FREE_NOTES[m]}]{win}{extra}")
    print(f"worker 当前模型 (profiles/workbuddy/config.yaml): {st['worker_model'] or '?'}")
    print(f"引擎 当前模型  (~/.codebuddy/settings.json):       {st['engine_model'] or '?'}")
    if st["recent_log"]:
        print("最近切换记录:")
        for r in st["recent_log"]:
            print("  " + json.dumps(r, ensure_ascii=False)[:160])
    return 0


def rotate_layer(layer: str, current: str, probes: dict, dry: bool) -> str:
    """Return action string. Never switches TO a model outside its free window;
    an expired free model currently in use is moved OFF to a still-in-window one.
    Non-quota failures (network blips) only switch after 2 consecutive fails."""
    kept, expired = free_now()
    if current not in FREE_ORDER:
        return f"skip (当前 {current or '?'} 不在限免清单，未动)"
    if current in expired:
        if not kept:
            return "expired (免费窗全部过期：无可切换目标，请人工处理)"
        for m in kept:
            if m not in probes:
                probes[m] = probe(m)
            if probes[m]["ok"]:
                if dry:
                    return f"WOULD switch off expired → {m}"
                writer = write_worker_model if layer == "worker" else write_engine_model
                ok, note = writer(m)
                _remember_prev(layer, current)
                log_event({"cmd": "guard", "layer": layer, "from": current, "to": m,
                           "ok": ok, "note": "moved off expired window; " + note})
                return f"switch off expired {current} → {m} ({'ok' if ok else 'FAILED: ' + note})"
        return f"expired {current} 但所有仍在窗内的模型不可用（人工处理）"
    if current not in probes:
        probes[current] = probe(current)
    if probes[current]["ok"]:
        _reset_soft_fail(layer, current)
        return "keep"
    p = probes[current]
    if not p.get("quota_like"):
        n = _bump_soft_fail(layer, current)
        if n < 2:
            log_event({"cmd": "guard", "layer": layer, "from": current, "to": None,
                       "ok": True, "note": f"non-quota failure #{n}; held: {p.get('detail','')[:160]}"})
            return f"keep (非额度类失败 #{n}，暂不切换: {p.get('detail','')[:60]})"
    _reset_soft_fail(layer, current)
    for m in kept:
        if m == current:
            continue
        if m not in probes:
            probes[m] = probe(m)
        if probes[m]["ok"]:
            if dry:
                return f"WOULD switch → {m}"
            writer = write_worker_model if layer == "worker" else write_engine_model
            ok, note = writer(m)
            _remember_prev(layer, current)
            log_event({"cmd": "guard", "layer": layer, "from": current, "to": m, "ok": ok, "note": note})
            return f"switch {current} → {m} ({'ok' if ok else 'FAILED: ' + note})"
    log_event({"cmd": "guard", "layer": layer, "from": current, "to": None, "ok": False,
               "note": "all in-window free models dead"})
    hint = "worker 将走 fallback 链(→DeepSeek)" if layer == "worker" else "引擎无免费模型可用：建议改派/等窗口重置"
    return f"all free dead ({hint})"


def cmd_guard(args) -> int:
    if not gateway_up():
        log_event({"cmd": "guard", "ok": False, "note": "gateway down"})
        print("gateway DOWN — 不改动任何配置。检查 supervisor 日志后重试（83-gateway-relaunch.ps1）。")
        return 3
    kept, expired = free_now()
    if expired:
        print("（免费窗已过期/未开启，不参与切换：" + ", ".join(expired) + "）")
    if not kept:
        log_event({"cmd": "guard", "ok": False, "note": "no free window open"})
        print("所有限免窗口均已过期/未开启——不改动配置，请人工选择模型。")
        return 2
    probes = {}
    results = {}
    rc = 0
    for layer, cur in (("worker", read_worker_model()), ("engine", read_engine_model())):
        act = rotate_layer(layer, cur, probes, args.dry)
        results[layer] = (cur, act)
        print(f"{layer:<7} {cur or '?'} → {act}")
        if ("FAILED" in act) or act.startswith(("all free dead", "expired")):
            rc = 2
    if not args.dry:
        log_event({"cmd": "guard", "ok": rc == 0,
                   "worker": {"model": results["worker"][0], "action": results["worker"][1]},
                   "engine": {"model": results["engine"][0], "action": results["engine"][1]}})
    print("(dry-run，未写入)" if args.dry else f"日志: {LOG}")
    return rc


def cmd_restore(args) -> int:
    """把 worker/引擎回切到 guard 记录的切换前模型（仅当该模型仍在免费窗内且可用）。"""
    st = _state_load()
    prev = st.get("prev") or {}
    if not prev:
        print("没有切换记录（prev 为空），无需回切")
        return 0
    kept, _expired = free_now()
    rc = 0
    for layer, model in (("worker", prev.get("worker")), ("engine", prev.get("engine"))):
        if not model:
            continue
        if model not in kept:
            print(f"{layer}: 原模型 {model} 已不在免费窗内，跳过")
            rc = 2
            continue
        if not probe(model)["ok"]:
            print(f"{layer}: 原模型 {model} 探测失败，跳过")
            rc = 2
            continue
        writer = write_worker_model if layer == "worker" else write_engine_model
        ok, note = writer(model)
        log_event({"cmd": "restore", "layer": layer, "to": model, "ok": ok, "note": note})
        print(f"{layer}: 回切 {model} ({'ok' if ok else 'FAILED: ' + note})")
        if ok:
            st.get("prev", {}).pop(layer, None)
        else:
            rc = 2
    _state_save(st)
    return rc


def cmd_pick(args) -> int:
    if not gateway_up():
        print("gateway-down", file=sys.stderr)
        return 1
    kept, _expired = free_now()
    for m in kept:
        if probe(m)["ok"]:
            print(m)
            return 0
    print("NO-FREE-MODEL-AVAILABLE", file=sys.stderr)
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("status"); p.add_argument("--json", action="store_true"); p.set_defaults(fn=cmd_status)
    p = sub.add_parser("guard"); p.add_argument("--dry", action="store_true"); p.set_defaults(fn=cmd_guard)
    p = sub.add_parser("pick"); p.set_defaults(fn=cmd_pick)
    p = sub.add_parser("restore"); p.set_defaults(fn=cmd_restore)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
