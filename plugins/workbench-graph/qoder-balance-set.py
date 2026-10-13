"""Record a hand-read Qoder Credits snapshot for the workbench graph box.

Qoder exposes no token-free usage API, so the number comes from the app's
「我的用量」 panel or the signed-in page https://qoder.cn/account/usage .

  python qoder-balance-set.py --remaining 4820 --total 6000 --note "应用内我的用量"
  python qoder-balance-set.py --show
"""

from __future__ import annotations

import argparse
import json
import os
import time

DEST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qoder-balance.json")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--remaining", type=int, help="Credits still available")
    ap.add_argument("--total", type=int, help="Credits in the current period")
    ap.add_argument("--plan", default="", help="plan tier name, optional")
    ap.add_argument("--note", default="", help="where the reading came from")
    ap.add_argument("--show", action="store_true", help="print the stored snapshot")
    a = ap.parse_args()

    if a.show:
        if not os.path.exists(DEST):
            print("no snapshot yet:", DEST)
            return 1
        print(open(DEST, encoding="utf-8").read())
        return 0

    if a.remaining is None or a.total is None:
        ap.error("--remaining and --total are required unless --show")
    if a.remaining < 0 or a.total <= 0 or a.remaining > a.total:
        ap.error("need 0 <= remaining <= total")

    now = time.time()
    payload = {
        "remaining": int(a.remaining),
        "total": int(a.total),
        "plan": a.plan,
        "note": a.note,
        "read_at": now,
        "read_at_str": time.strftime("%Y-%m-%d %H:%M:%S %z", time.localtime(now)),
        "source": "qoder 应用「我的用量」 或 https://qoder.cn/account/usage",
    }
    tmp = DEST + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, DEST)
    print("wrote", DEST)
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
