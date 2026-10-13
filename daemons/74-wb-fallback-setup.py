"""One-shot setup: give the workbuddy profile a free-first fallback chain + widen its bridge model list.

- fallback_providers = [hy4-preview-f@gateway, hy3@gateway, deepseek-flash@api.deepseek.com (last-resort, paid)]
  Hermes switches to the chain on quota/billing/rate-limit/5xx failures of the primary worker model.
- providers.custom.models += hy3  (so the drawer's 桥接模型 picker can also pick it)

Idempotent: re-running replaces the chain. Backs up config.yaml once. NEVER prints secret values (fingerprints only).

Run:  .venv/Scripts/python.exe .build/workbench/74-wb-fallback-setup.py
"""
import hashlib
import io
import os
import shutil
import sys

from ruamel.yaml import YAML

HOME = os.environ["LOCALAPPDATA"].replace("\\", "/") + "/hermes"
MAIN_CFG = f"{HOME}/config.yaml"
WB_DIR = f"{HOME}/profiles/workbuddy"
WB_CFG = f"{WB_DIR}/config.yaml"
BACKUP = f"{WB_CFG}.bak-quota-20261012"

GATEWAY = "http://127.0.0.1:8787/v1"


def fp(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:8] if s else "<empty>"


def main() -> int:
    y = YAML(typ="rt")
    y.preserve_quotes = True

    with open(MAIN_CFG, "r", encoding="utf-8") as fh:
        main_cfg = y.load(fh)
    ds_key = str((main_cfg.get("model") or {}).get("api_key") or "")
    if not ds_key.startswith("sk-"):
        print("ERROR: main config model.api_key not found/odd; abort")
        return 1

    if not os.path.exists(BACKUP):
        shutil.copy2(WB_CFG, BACKUP)
        print(f"backup -> {BACKUP}")

    with open(WB_CFG, "r", encoding="utf-8") as fh:
        wb = y.load(fh)

    old_chain = wb.get("fallback_providers")
    wb["fallback_providers"] = [
        {"provider": "custom", "model": "hy4-preview-f",
         "base_url": GATEWAY, "api_key": "codebuddy-local", "api_mode": "chat_completions"},
        {"provider": "custom", "model": "hy3",
         "base_url": GATEWAY, "api_key": "codebuddy-local", "api_mode": "chat_completions"},
        {"provider": "custom", "model": "deepseek-flash",
         "base_url": "https://api.deepseek.com/v1", "api_key": ds_key, "api_mode": "chat_completions"},
    ]

    models = wb.setdefault("providers", {}).setdefault("custom", {}).setdefault("models", [])
    added_hy3 = "hy3" not in list(models)
    if added_hy3:
        models.append("hy3")

    buf = io.StringIO()
    y.dump(wb, buf)
    tmp = WB_CFG + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\r\n") as fh:
        fh.write(buf.getvalue())
    os.replace(tmp, WB_CFG)

    # verify round-trip
    with open(WB_CFG, "r", encoding="utf-8") as fh:
        again = y.load(fh)
    chain = again.get("fallback_providers") or []
    ok = (
        len(chain) == 3
        and [e.get("model") for e in chain] == ["hy4-preview-f", "hy3", "deepseek-flash"]
        and fp(str(chain[2].get("api_key"))) == fp(ds_key)
        and "hy3" in list(again["providers"]["custom"]["models"])
    )
    print("old chain len:", 0 if old_chain is None else len(old_chain))
    print("new chain:", [f"{e.get('model')}@{e.get('base_url')}" for e in chain])
    print("bridge models:", list(again["providers"]["custom"]["models"]))
    print("deepseek key fingerprint:", fp(ds_key), "(matches main:", fp(str(chain[2].get('api_key'))), ")")
    print("hy3 added to bridge list:", added_hy3)
    print("VERIFY:", "OK" if ok else "FAILED")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
