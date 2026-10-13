# 卡：隐藏态流式渲染降频补丁 P1（use-message-stream ×2 文件定点修改）

## 执行引擎要求（必须声明）
优先 **Claude Code 软件自身执行**：`claude -p "<本任务简报文本>"`（Claude Code CLI 已配好模型与权限）。
若 CLI 不便于做定点改写，可退回 **Hermes 工作进程代执行**（工作区文件工具改副本）——但完成评论必须如实声明「软件自身执行」或「Hermes 工作进程代执行」，并给出证据（命令原文/关键输出）。**不得**让软件打开 GUI。

## 背景（诊断结论，直接采信，无需复核）
工作台流式输出期间渲染进程主线程 ~66% 占用（仪器实测）。**窗口最小化/遮挡时主进程在回合期间会解除节流（stream-throttle.ts）→ 渲染器对没人看得到的流照常全速处理 = 纯浪费**。修法：窗口不可见时把流增量合批间隔放宽到 750ms；回可见时既有 `visibilitychange`/`focus` 逻辑会立即补冲队列，观感不变。

## 定点修改规格（只改这两处，不得改动其它内容）

### 文件 1：use-message-stream/utils.ts
路径：`C:/Users/<用户名>/Desktop/hermes-agent-main/apps/desktop/src/app/session/hooks/use-message-stream/utils.ts`
基线 md5：`69fa9a0dcd0812322dfe4e0155edd597`
在 `export const MAX_STREAM_FLUSH_GAP_MS = 250` 的注释块与声明之后，追加：

```ts
// Flush gap once the window cannot be seen (minimized / occluded / hidden).
// The adaptive floor above only pays for itself when somebody is watching;
// hidden, every flush is pure renderer cost. The visibilitychange/focus
// effect in use-message-stream drains the queue immediately on return, so a
// hidden window never strands a delta.
export const HIDDEN_STREAM_FLUSH_MS = 750
```

### 文件 2：use-message-stream/index.ts
路径：`C:/Users/<用户名>/Desktop/hermes-agent-main/apps/desktop/src/app/session/hooks/use-message-stream/index.ts`
基线 md5：`cbf8ff113296b7a44ab18608569a8b23`

**(a) 现第 52 行**（import 自 './utils'）替换为：
```ts
import { completionErrorText, delegateTaskPayloads, HIDDEN_STREAM_FLUSH_MS, MAX_STREAM_FLUSH_GAP_MS, STREAM_DELTA_FLUSH_MS } from './utils'
```

**(b) 新增一行 import**（放进现有 `@/lib/*` import 群，保持该文件既有排序风格）：
```ts
import { RENDERER_ANIMATIONS_PAUSED_ATTRIBUTE } from '@/lib/renderer-loop-pause'
```

**(c) 现约 370–375 行的 adaptiveFloor 块**：
原文——
```ts
    const sinceLast = performance.now() - lastFlushAtRef.current

    const adaptiveFloor = Math.min(
      Math.max(STREAM_DELTA_FLUSH_MS, lastFlushCostRef.current * 3),
      MAX_STREAM_FLUSH_GAP_MS
    )
```
替换为——
```ts
    const sinceLast = performance.now() - lastFlushAtRef.current

    // A window nobody can see cannot show the transcript, so the adaptive
    // floor buys nothing there — stream at a coarse hidden cadence instead.
    // NOT document.hidden: while a turn is in flight the main process lifts
    // background throttling (stream-throttle.ts), and setBackgroundThrottling
    // pins the Page Visibility API to 'visible' even for a minimized window.
    // The paused attribute is the app's own authoritative window-state report
    // (main.tsx mirrors the minimized / not-visible payload onto :root). The
    // visibilitychange / focus effect below drains the queue on return, so a
    // hidden window never strands a delta.
    const windowHidden =
      typeof document !== 'undefined' &&
      (document.documentElement.hasAttribute(RENDERER_ANIMATIONS_PAUSED_ATTRIBUTE) ||
        document.visibilityState === 'hidden')

    const adaptiveFloor = windowHidden
      ? HIDDEN_STREAM_FLUSH_MS
      : Math.min(
          Math.max(STREAM_DELTA_FLUSH_MS, lastFlushCostRef.current * 3),
          MAX_STREAM_FLUSH_GAP_MS
        )
```

## 交付物（落在你自己的工作区，再复制到 `C:\Users\<用户名>\Desktop\工作区\Hermes工作台\tasks\<你的卡id>\`）
1. `HIDDEN_FIX.md`：三处修改的前后对照；并解释**为什么用 `data-renderer-animations-paused` 属性而不用 `document.hidden`**（要点：回合进行中 `setBackgroundThrottling(false)` 会把 Page Visibility 钉在 visible，`document.hidden` 永不生效；属性来自主进程窗口状态通道）。
2. 两个**改后完整文件**（`utils.ts`、`index.ts` 全量副本）。
3. `HIDDEN_FIX.diff`：对上述两个原始文件的 unified diff（基线 md5 见上，先校验再改）。
4. `verify.txt`：`grep -n` 证明三处新代码在位的行号输出；如环境可用再附 `npx tsc --noEmit -p apps/desktop/tsconfig.json` 的结果（不可用则写明原因即可）。

## 硬约束
- **不要直接修改仓库文件**（本体负责落盘与构建）；只在你的工作区产出副本与 diff。
- 行号仅供参考，一律以**内容匹配**为准；不得改公开签名、不得触碰 adaptiveFloor 块的其它逻辑。
- 完成评论必须包含：①引擎命令原文 ②engine 输出关键行 ③交付物路径 ④引擎声明。完成时 `kanban complete <id> --summary "..."`。
