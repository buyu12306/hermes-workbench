import os

RULE = (
    "\n\n## 共享工作区（工作台规则）\n"
    "产物统一放 C:\\Users\\<用户名>\\Desktop\\工作区\\Hermes工作台\\tasks\\<task_id>\\"
    "（先看该目录 README）；可读其他任务目录，只写自己的；公用素材放 shared\\；"
    "卡上评论/总结写共享工作区里的路径。\n"
)

base = os.path.join(os.environ["LOCALAPPDATA"], "hermes", "profiles")
names = ["claude-code", "deepseek-harness", "qoder", "trae", "trae-solo", "workbuddy"]
for n in names:
    p = os.path.join(base, n, "SOUL.md")
    try:
        txt = open(p, "r", encoding="utf-8").read()
    except Exception as e:
        print(n, "READ-FAIL", type(e).__name__)
        continue
    if "共享工作区" in txt:
        print(n, "already-has-rule")
        continue
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(RULE)
    print(n, "rule-appended")
