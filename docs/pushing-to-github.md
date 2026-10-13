# 推送到 GitHub（本机特有配方）

本机网络：直连 `github.com` 不通（curl 返回 000、超时）；必须走本地代理 `http://127.0.0.1:7877`（MyClash，实测 200 / 0.6s）。

> 注：文中 `<用户名>`、`<你的GitHub用户名>` 均为占位符，使用前替换为你自己的实际值。

本机 `~/.gitconfig` 有一条全局规则：

```
url.https://ghfast.top/https://github.com/.insteadOf = https://github.com/
```

作用：让 clone / 下载走 ghfast.top 镜像。**clone 没问题，但 `git push` 走该镜像会无限卡住**（receive-pack 不被支持）。这就是 2026-10-12 前两次 push 各挂 420 秒的根因。

## 可用配方（2026-10-12 实测：1.27 MB 包，10 秒推成）

### 1. 远端 URL 用 userinfo 形式绕过 insteadOf

```bash
git remote set-url origin "https://<你的GitHub用户名>@github.com/<你的GitHub用户名>/hermes-workbench.git"
```

- `insteadOf` 是前缀匹配：`https://<你的GitHub用户名>@github.com/...` 不以 `https://github.com/` 开头 → 不触发改写。
- **不要用 `https://github.com:443/...`**：`insteadOf` 确实绕过了，但 gh 的凭据助手不认带端口的 host，会直接报 `could not read Username`。

### 2. 干净凭据链（必须先清掉全局 GCM，否则卡在不可见的 UI 提示上）

```bash
export GIT_CONFIG_COUNT=2
export GIT_CONFIG_KEY_0=credential.helper   GIT_CONFIG_VALUE_0=
export GIT_CONFIG_KEY_1=credential.helper   GIT_CONFIG_VALUE_1="!'C:/Users/<用户名>/AppData/Local/hermes/tools/gh/bin/gh.exe' auth git-credential"
```

`GIT_CONFIG_VALUE_0=`（空值）重置继承来的 helper 列表，再挂 gh 的 helper——顺序即优先级，缺一不可。

### 3. 网络与超时护栏

```bash
export GIT_TERMINAL_PROMPT=0
export HTTPS_PROXY=http://127.0.0.1:7877 HTTP_PROXY=http://127.0.0.1:7877 NO_PROXY='127.0.0.1,localhost,::1'
timeout -s KILL 300 git push -u origin main --verbose
```

- `GIT_TERMINAL_PROMPT=0`：任何要交互的凭据询问直接失败，而不是挂起。
- MSYS 的 `timeout` 普通 `TERM` 杀不死 git（实测挂满 240s），**必须 `-s KILL`**。

## 验证

```bash
git ls-remote origin            # 应列出 main 的 sha
gh api repos/<你的GitHub用户名>/hermes-workbench/git/trees/main?recursive=1 \
  --jq '[.tree[] | select(.type=="blob")] | length'
```

## 一键脚本

本仓库 `tools/push-workbench2.sh` 为同款配方的可复用脚本（已占位化）：将其中的 `<用户名>` 替换为你的实际值，确认 `origin` 为 userinfo 形式、代理端口无误后，在仓库根目录用 bash 执行即可；日志写在脚本内 `LOG=` 指定处。
