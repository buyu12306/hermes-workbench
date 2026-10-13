# -*- coding: utf-8 -*-
"""Patience login helper: prints auth URL, waits up to 1h for browser approval, saves session."""
import sys
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)

from codebuddy_proxy.codebuddy_client_demo import CodeBuddyClient

print("CLIENT-INIT", flush=True)
try:
    c = CodeBuddyClient()
except TypeError:
    import inspect
    print("INIT-SIGNATURE:", inspect.signature(CodeBuddyClient.__init__), flush=True)
    raise
print("SESSION-FILE:", c.session_file, flush=True)
print("ENDPOINT:", c.endpoint, flush=True)
c.login(open_browser=True, timeout=3600)
print("LOGIN-FLOW-RETURNED", flush=True)
