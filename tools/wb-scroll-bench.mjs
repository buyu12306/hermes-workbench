// Scroll-cost matrix: wheel-scroll the thread viewport under three configs and
// trace the renderer. Configs:
//   A as-shipped   – field animating, transparent surfaces
//   B no-field     – field layers hidden (surfaces still transparent)
//   C pre-field    – field hidden + surfaces restored opaque (approx. old app)
//   D static-field – layers visible, animations off
const port = Number(process.env.HERMES_DESKTOP_CDP_PORT || 9333)
const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json()
const main = targets.find((t) => t.type === 'page' && (t.url || '').startsWith('file://'))
const ws = new WebSocket(main.webSocketDebuggerUrl)
let id = 0
const pending = new Map()
let traceBuf = []
ws.addEventListener('message', (ev) => {
  const m = JSON.parse(ev.data)
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id) }
  else if (m.method === 'Tracing.dataCollected') traceBuf.push(...(m.params.value || []))
})
await new Promise((r) => ws.addEventListener('open', r))
const send = (method, params, timeoutMs = 40000) => new Promise((res) => {
  const i = ++id
  pending.set(i, res)
  ws.send(JSON.stringify({ id: i, method, params }))
  setTimeout(() => { if (pending.has(i)) { pending.delete(i); res({ __timeout: method }) } }, timeoutMs)
})
const evalv = async (expression) => {
  const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
  if (r.result?.exceptionDetails) console.log('EXC:', (r.result.exceptionDetails.exception?.description || '').slice(0, 200))
  return r.result?.result?.value
}
const setTest = (css) => evalv(`(() => { let el = document.getElementById('wb-scroll-test'); if (!el) { el = document.createElement('style'); el.id = 'wb-scroll-test'; document.head.appendChild(el); } el.textContent = ${JSON.stringify(css)}; return 'ok' })()`)

const G = ':root:has([data-contrib-shell]):not(:has([data-hud-shell]))'
const CFG = {
  A: '',
  B: `${G}::before,${G}::after,${G} body::after{display:none !important}`,
  C: `${G}::before,${G}::after,${G} body::after{display:none !important} ` +
     `${G}{--ui-chat-surface-background: var(--ui-bg-chrome) !important; --ui-sidebar-surface-background: var(--ui-bg-sidebar) !important; --ui-editor-surface-background: var(--ui-bg-chrome) !important} ` +
     `${G} body{background: var(--ui-bg-chrome) !important} ` +
     `${G} [data-contrib-shell], ${G} [data-slot='sidebar-wrapper']{background-color: var(--ui-bg-chrome) !important}`,
  D: `${G}::before,${G}::after,${G} body::after{animation:none !important}`
}

const key = ['RasterTask', 'Rasterize', 'GPUTask', 'CompositeLayers', 'BeginMainFrame', 'DroppedFrame', 'Graphics.Pipeline', 'Scroll']
const summarize = (events) => {
  const by = new Map()
  for (const e of events) {
    if (e.ph !== 'X') continue
    const rec = by.get(e.name) || { n: 0, dur: 0 }
    rec.n++; rec.dur += e.dur || 0
    by.set(e.name, rec)
  }
  const pick = {}
  for (const k of key) {
    let n = 0, dur = 0
    for (const [name, rec] of by) if (name.includes(k)) { n += rec.n; dur += rec.dur }
    pick[k] = { n, ms: +(dur / 1000).toFixed(1) }
  }
  return pick
}

const scrollSweep = async () => {
  await evalv(`(() => { const s = document.querySelector('[data-slot="aui_thread-viewport"]'); s.scrollTop = Math.max(0, Math.round(s.scrollHeight / 2)); return s.scrollTop })()`)
  await new Promise(r => setTimeout(r, 300))
  traceBuf = []
  await send('Tracing.start', { categories: 'devtools.timeline,cc,benchmark,viz', transferMode: 'ReportEvents' })
  for (let i = 0; i < 30; i++) {
    await send('Input.dispatchMouseEvent', { type: 'mouseWheel', x: 870, y: 400, deltaX: 0, deltaY: i < 15 ? 200 : -200 })
    await new Promise(r => setTimeout(r, 120))
  }
  await send('Tracing.end')
  await new Promise(r => setTimeout(r, 1200))
  const sc = await evalv(`(() => { const s = document.querySelector('[data-slot="aui_thread-viewport"]'); return { top: Math.round(s.scrollTop), moved: true } })()`)
  return { summary: summarize(traceBuf), events: traceBuf.length, endTop: sc && sc.top }
}

for (const cfg of ['A', 'B', 'C', 'D']) {
  await evalv(`document.documentElement.removeAttribute('data-renderer-animations-paused'); 'on'`)
  await setTest(CFG[cfg])
  await new Promise(r => setTimeout(r, 700))
  const res = await scrollSweep()
  const s = res.summary
  console.log(`--- ${cfg} (${res.events} events, endTop=${res.endTop}) ---`)
  console.log('   raster n=' + s.RasterTask.n + ' ms=' + s.RasterTask.ms +
    ' | gpu n=' + s.GPUTask.n + ' ms=' + s.GPUTask.ms +
    ' | composite n=' + s.CompositeLayers.n + ' ms=' + s.CompositeLayers.ms +
    ' | bmf n=' + s.BeginMainFrame.n + ' ms=' + s.BeginMainFrame.ms)
  console.log('   dropped=' + JSON.stringify(s.DroppedFrame) + ' pipeline=' + JSON.stringify(s['Graphics.Pipeline']))
}
await setTest('')
await evalv(`document.getElementById('wb-scroll-test')?.remove(); document.documentElement.setAttribute('data-renderer-animations-paused',''); 'done'`)
console.log('done')
process.exit(0)
