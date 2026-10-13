# gateway — 本地免费模型网关（codebuddy-gateway）

为 WorkBuddy 桥提供**免费模型出口**：本机 HTTP 服务，把腾讯限免模型（step-5-preview / hy4-preview-f / hy3）暴露为 OpenAI 兼容接口 `http://127.0.0.1:8787/v1`。

## 组件

| 文件 | 说明 |
|---|---|
| `supervisor.ps1` | **监管进程 v2**（由「启动」文件夹的 `CodeBuddy_Gateway.vbs` 拉起，无窗口）。职责：拉起/重启网关子进程、**HTTP 健康检查**、崩溃退避（10s 起倍增，封顶 300s）、日志轮转（2MB）、退出机制 |
| `login_patient.py` | 会话失效时重新登录：打印授权链接、等待浏览器确认（最长 1 小时）、保存会话 |
| `hermes-gateway-service/` | **Hermes 消息网关**（与本网关无关的另一件事）：`Hermes_Gateway.vbs/cmd` 是 `hermes_cli.main gateway run` 的启动器，承载 IM 通道（含 QQ），由 `83-gateway-relaunch.ps1` 负责重启 |

## supervisor.ps1 关键行为

- 子进程：`<uv> run --with workbuddy2api python -u -m codebuddy_proxy --host 127.0.0.1 --port 8787 --log-file proxy.jsonl`
  （`uv` 默认路径 `C:\Users\<用户名>\.local\bin\uv.exe`，工作目录 `%LOCALAPPDATA%\hermes\codebuddy-gateway`）
- 健康检查：`GET http://127.0.0.1:8787/v1/models`（带 `Authorization: Bearer codebuddy-local`，本机占位令牌）**必须返回 200**；进程在但 HTTP 不通同样算挂
- 稳态：每 30s 探活，连续 2 次失败重启子进程（指数退避）
- 停止：在 `%LOCALAPPDATA%\hermes\codebuddy-gateway\gateway.stop` 放一个文件 → 监管杀掉子进程树、消费标记、自身退出（干净停服，不会自动复活）
- 日志：`supervisor.log`（自身）、`server.out/err`（子进程）、`proxy.jsonl`（网关请求日志），均 2MB 轮转

## 重启（标准姿势）

```powershell
# 精确停掉旧监管 + 子进程树（按路径/进程名双重匹配，绝不用模糊匹配）
powershell -NoProfile -ExecutionPolicy Bypass -File <SCRATCH>\restart-supervisor.ps1
# 该脚本：杀旧 → 等端口 8787 释放 → 清残留 → 经启动 VBS 拉起一个且仅一个监管
```

> 注意：**不要**用 `taskkill /IM …` 按进程名杀；查询用 `Get-CimInstance` 时必须加进程名白名单（详见 `daemons/README.md` 第 5 节教训 2）。

## 验证

```bash
curl -s -H 'Authorization: Bearer codebuddy-local' http://127.0.0.1:8787/v1/models | head -c 200
tail -5 %LOCALAPPDATA%\hermes\codebuddy-gateway\supervisor.log
# 期望：HTTP 200；日志最后几行为 "supervisor start" → "child pid …" → "gateway healthy"，此后不再刷 "child exited"
```

## 与额度守卫联动

`daemons/73-wb-quota.py` 负责模型限免窗口管理：过期模型不会被切到；网关不可达时 guard 退出码 3 且不改配置（先修网关再守额度）。网关掉线自愈入口：
`daemons/83-gateway-relaunch.ps1` 管的是 **Hermes 消息网关**；本网关的自愈由 `supervisor.ps1` 自己完成，重装/重启用上面的 restart 脚本。
