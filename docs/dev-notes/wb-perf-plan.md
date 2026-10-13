# 工作台卡顿诊断与优化 — 2026-10-12 晚（现场笔记）

## 已确证（有仪器证据）
1. **流式输出期间渲染进程 ~8s/12s 主线程占用**（CDP Performance.getMetrics：task=+7.9~8.2s per 12s，其中 script 3-4.6s、style recalc 1.5-2.6s；layout 极低）。
   - DOM 变动全部指向对话文本（P./LI./CODE./wrap-anywhere 段落）= 流式 markdown 渲染提交。
   - 观测器时间线：hot 样本（renderer 90-130%）与我（代理）流式输出的时段重合；cold（10-25%）与工具执行间隙重合。
2. **窗口最小化时（p=""，hidden）照常全速处理流**——主进程 stream-throttle 在回合期间解除窗口节流（设计如此，防"回复卡住"）。此时渲染无人可见 = 纯浪费。
3. 应用自身已高度优化：30Hz 自适应合批（33ms 基/成本×3/250ms 上限=最低 4 次/秒）、分块 markdown（200 行）、shiki 延迟高亮、render-weight 转录预算（"Show earlier" 分页）、decode 效果有界（22Hz 但一次性解析后自停）——不是新手工程。
4. 排除项：场 CSS（:has 选择器）无辜——合成基准 150 次突发 0.000s 样式重算；arc/shimmer/glyph/decode 等小动画不是主犯（an=0 时也热）；邻居进程（chrome 74%/msedge 52%+/电脑管家）不归我们管但同在抢 CPU。
5. 轻量常驻：cold 时渲染 10-25%（待优化后复测）。

## 决策的补丁 P1（低风险，零视觉代价）
`apps/desktop/src/app/session/hooks/use-message-stream/index.ts` scheduleDeltaFlush：
- 现状：adaptiveFloor = min(max(33, lastCost*3), 250)，定时器驱动。
- 补丁：`document.visibilityState === 'hidden'` 时改用 HIDDEN_STREAM_FLUSH_MS（750ms）；可见时保持原逻辑。
- 回可见时已有 visibilitychange → flushPendingDeltas 立即补帧（保留）。
- 常数放 `use-message-stream/utils.ts`（STREAM_DELTA_FLUSH_MS=33、MAX_STREAM_FLUSH_GAP_MS=250 旁）。
- 预期：用户不看窗口（最小化/被遮挡）时流处理成本降至 ~1/7~1/10；回窗口瞬间补齐，观感不变。

## 验证方案
1. 构建 + 重启工作台（步骤见 hermes-workbench-build 技能）。
2. 同款仪器复测：wb-stream-probe.mjs（观察 hidden 段 task/12s 是否塌到 <1-2s）+ wb-idle-watch.sh（renderer 热样本应显著低于 90-130%）。
3. 观察可见时段（挂前台读屏）流式体验：文本增速、滚动跟手。

## 备选 P2（待用户拍板，改可感知行为）
MAX_STREAM_FLUSH_GAP_MS 250→400~500（重载阶段文本 4/s→2.5/s，主线程减半）。默认不动。

## 部署注意
- 工作台当前在运行（用户正用它聊天）。构建后需重启应用；重启会刷新聊天窗口（会话与后端不受影响）。
- 绝不能 `hermes gateway restart`；应用拉起方式见技能。
