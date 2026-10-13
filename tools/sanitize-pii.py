#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""sanitize-pii.py — 把仓库文本中的个人标识替换为占位符（幂等；保持原编码与行尾）。

用法: python sanitize-pii.py [repo_dir]

使用前先把下面两个标识改成你自己的值（本仓库的脱敏就是用该工具完成的）:
  WIN_USER = Windows 用户名（即 C:\\Users\\<WIN_USER> 中的 <WIN_USER>）
  GH_USER  = GitHub 账号名（出现在文档/推送脚本中的账号）
替换:
  C:\\Users\\<WIN_USER>  /  C:/Users/<WIN_USER>  /  /c/Users/<WIN_USER>   ->  前缀 + <用户名>
  <GH_USER>（含 userinfo 形式）                                          ->  <你的GitHub用户名>
"""
import re
import sys
from pathlib import Path

WIN_USER = "your_username"          # <- 改成你自己的 Windows 用户名
GH_USER = "your_github_account"     # <- 改成你自己的 GitHub 账号名

REPO = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
PLACE_USER = "<用户名>"
PLACE_GH = "<你的GitHub用户名>"
SELF = Path(__file__).resolve()

rx_win = re.compile(r"(?i)([a-z]:[\\/]{1,2}users[\\/]{1,2})" + re.escape(WIN_USER))
rx_posix = re.compile(r"(?i)(/c/users/)" + re.escape(WIN_USER))


def decode(b: bytes):
    if b.startswith(b"\xef\xbb\xbf"):
        return b.decode("utf-8-sig"), "utf-8-sig"
    try:
        return b.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        pass
    try:
        return b.decode("gbk"), "gbk"
    except UnicodeDecodeError:
        return None, None


changed, leftovers = [], []
for f in sorted(REPO.rglob("*")):
    if not f.is_file():
        continue
    rel = f.relative_to(REPO)
    if rel.parts and rel.parts[0] == ".git":
        continue
    if f.resolve() == SELF:
        continue
    b = f.read_bytes()
    if b"\x00" in b[:4096]:          # binary
        continue
    t, enc = decode(b)
    if t is None:
        print("[skip-undecodable]", rel)
        continue
    o = t
    n_win = len(rx_win.findall(t))
    t = rx_win.sub(lambda m: m.group(1) + PLACE_USER, t)
    n_pos = len(rx_posix.findall(t))
    t = rx_posix.sub(lambda m: m.group(1) + PLACE_USER, t)
    n_gh = t.count(GH_USER)
    t = t.replace(GH_USER, PLACE_GH)
    if t != o:
        f.write_bytes(t.encode(enc))
        changed.append("%s  (win:%d posix:%d gh:%d)" % (rel, n_win, n_pos, n_gh))
    for i, line in enumerate(t.splitlines(), 1):
        if WIN_USER in line or GH_USER in line:
            leftovers.append("%s:%d: %s" % (rel, i, line.strip()[:130]))

print("== changed: %d ==" % len(changed))
for c in changed:
    print("  " + c)
print("== leftovers: %d ==" % len(leftovers))
for l in leftovers[:80]:
    print("  " + l)
