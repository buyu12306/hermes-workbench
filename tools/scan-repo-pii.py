#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""scan-repo-pii.py — 对仓库做个人信息/敏感信息全量扫描（工作区 + git 历史）。

用法: python scan-repo-pii.py [repo_dir]
使用前把下面两个标识改成你自己的值（用来检查它们是否还有残留）。
报告写到当前目录 repo-pii-scan.txt。
"""
import re
import subprocess
import sys
from pathlib import Path

WIN_USER = "your_username"          # <- 改成你自己的 Windows 用户名
GH_USER = "your_github_account"     # <- 改成你自己的 GitHub 账号名

REPO = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
OUT = Path("repo-pii-scan.txt")
SELF = Path(__file__).resolve()
out = []


def p(s=""):
    out.append(str(s))


PATTERNS = [
    ("win_username", re.compile(re.escape(WIN_USER))),
    ("gh_account", re.compile(re.escape(GH_USER))),
    ("email", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("mac", re.compile(r"\b[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}\b")),
    ("private_ip", re.compile(r"\b(?:10\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])|192\.168)\.\d{1,3}\.\d{1,3}\b")),
    ("cn_mobile", re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")),
    ("api_keyish", re.compile(r"(?:sk|gh[opsu])[-_][A-Za-z0-9_-]{16,}")),
    ("jwt", re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")),
    ("bearer", re.compile(r"[Bb]earer\s+([A-Za-z0-9._~+/-]{16,}=*)")),
    ("qq_ref", re.compile(r"[Oo]pen[ _-]?[Ii][Dd]|QQ_APP|qqbot")),
    ("hostname", re.compile(r"DESKTOP-[A-Z0-9]{4,}", re.I)),
    ("session_id", re.compile(r"\b20\d{6}_\d{6}_[0-9a-f]{6}\b")),
]


def is_binary(b: bytes) -> bool:
    return b"\x00" in b[:4096]


p("=== SCAN REPORT ===")
p(f"repo: {REPO}")
p()

# ---------- 1) working tree scan ----------
hits = {name: [] for name, _ in PATTERNS}
files_user = {}
secret_val_lines = []
files_scanned = 0
for f in sorted(REPO.rglob("*")):
    if f.is_dir():
        continue
    rel = f.relative_to(REPO)
    if rel.parts[0] == ".git":
        continue
    if f.resolve() == SELF or f.name in ("scan-repo-pii.py", "sanitize-pii.py"):
        continue
    try:
        b = f.read_bytes()
    except Exception as e:
        p(f"[skip] {rel}: {e}")
        continue
    if is_binary(b):
        continue
    files_scanned += 1
    try:
        text = b.decode("utf-8", errors="replace")
    except Exception:
        continue
    for i, line in enumerate(text.splitlines(), 1):
        for name, rx in PATTERNS:
            if rx.search(line):
                hits[name].append((str(rel), i, line.strip()[:160]))
        if WIN_USER in line:
            files_user[str(rel)] = files_user.get(str(rel), 0) + 1
        if re.match(r"(?i)^\s*(api_key|apikey|token|password|secret|ANTHROPIC_AUTH_TOKEN|DEEPSEEK_API_KEY)\s*[:=]", line):
            secret_val_lines.append((str(rel), i, line.strip()[:140]))

p(f"files_scanned={files_scanned}")
p()
for name, _ in PATTERNS:
    n = len(hits[name])
    p(f"-- pattern {name}: {n} hits")
    if name == "win_username":
        for fn, c in sorted(files_user.items(), key=lambda x: -x[1]):
            p(f"   {c:4d}  {fn}")
    else:
        for (fn, i, ln) in hits[name][:8]:
            p(f"   {fn}:{i}: {ln}")
    p()

# ---------- 2) secret-value audit ----------
p("=== key/token VALUE audit (distinct RHS) ===")
vals = {}
for fn, i, ln in secret_val_lines:
    v = ln.split(":", 1)[-1] if ":" in ln else ln
    v = v.strip().strip('"').strip("'")
    key = v[:60]
    vals.setdefault(key, []).append(fn)
for v, fns in sorted(vals.items(), key=lambda x: -len(x[1])):
    p(f"   [{len(fns)}x] {v[:80]}   e.g. {fns[0]}")
p()

# ---------- 3) risky file types ----------
p("=== risky file inventory (db/log/env/pem/key/bak) ===")
risky = []
for f in sorted(REPO.rglob("*")):
    if f.is_dir() or ".git" in f.relative_to(REPO).parts:
        continue
    n = f.name.lower()
    if n.endswith((".db", ".log", ".sqlite", ".sqlite3", ".pem", ".key", ".bak")) or n.startswith(".env"):
        risky.append(str(f.relative_to(REPO)))
p("   " + ("\n   ".join(risky) if risky else "(none)"))
p()

# ---------- 4) git history scan ----------
p("=== git history scan (all revs, -l file list) ===")
revs = subprocess.run(["git", "rev-list", "--all"], cwd=REPO, capture_output=True, text=True).stdout.split()
p(f"revs: {revs}")
hist_pat = "|".join([
    re.escape(WIN_USER), re.escape(GH_USER),
    r"(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}",
    r"gh[opsu]_[A-Za-z0-9]{20,}", r"sk-[A-Za-z0-9]{20,}", r"DESKTOP-[A-Z0-9]{4,}",
])
r = subprocess.run(["git", "grep", "-l", "-I", "-E", hist_pat] + revs, cwd=REPO, capture_output=True, text=True)
p(f"files in history matching critical patterns: {len(r.stdout.splitlines())}")
for ln in r.stdout.splitlines()[:80]:
    p(f"   {ln}")
if r.returncode not in (0, 1):
    p(f"git grep rc={r.returncode} err={r.stderr[:400]}")
p()

OUT.write_text("\n".join(out), encoding="utf-8")
print("\n".join(out[:8]))
print(f"... full report: {OUT} ({len(out)} lines)")
print(f"win_username files: {len(files_user)}; email hits: {len(hits['email'])}; mac: {len(hits['mac'])}; keyish: {len(hits['api_keyish'])}; history_files: {len(r.stdout.splitlines())}")
