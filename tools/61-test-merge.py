import re, tempfile, os

ENTRY = lambda model: ("- id: agent-default-model\n"
                       "  name: \"@deepseek-ai/dsh-agent-default-model\"\n"
                       "  config:\n"
                       "    provider: deepseek-official\n"
                       f"    model: {model}\n"
                       "    reasoningEffort: high\n")

def merge(old, model):
    m = re.search(r"- id: agent-default-model\n(?:[ \t]+[^\n]*\n|\n)*", old)
    if m:
        old = old[:m.start()] + old[m.end():]
    old = re.sub(r"^\[\]\s*$", "", old, flags=re.M).strip("\n")
    header = "# patch header\n"
    return (old + "\n\n" if old else header) + ENTRY(model)

# case 1: fresh [] file with comments
t1 = merge("# comment\n[]\n", "deepseek-v4-pro")
print("case1 other-entries=0, has-entry:", "agent-default-model" in t1, "| no [] left:", "[]" not in t1)

# case 2: replace existing entry + keep sibling entries
old2 = merge("# h\n", "deepseek-flash") + "\n- id: other-entry\n  config:\n    foo: 1\n"
t2 = merge(old2, "deepseek-v4-pro")
print("case2 model swapped:", "model: deepseek-v4-pro" in t2, "| sibling kept:", "other-entry" in t2, "| old model gone:", "deepseek-flash" not in t2)

# case 3: injection blocked by route-level regex
bad = "x\n  injected: true"
print("case3 regex rejects:", not bool(re.match(r"^[A-Za-z0-9._\-]+$", bad)))
print("case3 regex accepts:", bool(re.match(r"^[A-Za-z0-9._\-]+$", "deepseek-v4-pro")))

# case 4: idempotent (merge twice = stable)
t4a = merge(t2, "deepseek-flash")
t4b = merge(t4a, "deepseek-flash")
print("case4 idempotent:", t4a == t4b)
