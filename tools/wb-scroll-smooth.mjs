// Scroll-smoothness matrix via screencast frame cadence during a uniform wheel sweep.
// Configs: A as-shipped | B field hidden | C field hidden + opaque surfaces (pre-field)
const port = Number(process.env.HERMES_DESKTOP_CDP_PORT || 9333)
const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json()
const main = targets.find((t) => t.type === 'page' && (t.url || '').startsWith('file://'))
const ws = new WebSocket(main.webSocketDebuggerUrl)
let id = 0
const pending = new Map()
const frameTimes = []
ws.addEventListener('message', (ev) => {
  const m = JSON.parse(ev.data)
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id) }
  else if (m.method === 'Page.screencastFrame') {
    frameTimes.push(Date.now())
    ws.send(JSON.stringify({ id: ++id, method: 'Page.screencastFrameAck', params: { sessionId: m.params.sessionId } }))
  }
})
await new Promise((r) => ws.addEventListener('open', r))
const send = (method, params, timeoutMs = 30000) => new Promise((res) => {
  const i = ++id
  pending.set(i, res)
  ws.send(JSON.stringify({ id: i, method, params }))
  setTimeout(() => { if (pending.has(i)) { pending.delete(i); res({ __timeout: method }) } }, timeoutMs)
})
const evalv = async (expression) => {
  const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
  if (r.result?.exceptionDetails) console.log('EXC:', (r.result.exceptionDetails.exception?.description || '').slice(0, 160))
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
     `${G} [data-contrib-shell], ${G} [data-slot='sidebar-wrapper']{background-color: var(--ui-bg-chrome) !important}`
}

const scrollTest = async (tag) => {
  await evalv(`document.documentElement.removeAttribute('data-renderer-animations-paused'); 'on'`)
  await new Promise(r => setTimeout(r, 500))
  frameTimes.length = 0
  await send('Page.startScreencast', { format: 'jpeg', quality: 50, everyNthFrame: 1 })
  await new Promise(r => setTimeout(r, 800))              // idle baseline (field animating)
  const idleFrames = frameTimes.length
  frameTimes.length = 0
  const t0 = Date.now()
  for (let i = 0; i < 24; i++) {
    await send('Input.dispatchMouseEvent', { type: 'mouseWheel', x: 870, y: 400, deltaX: 0, deltaY: i < 12 ? 240 : -240 })
    await new Promise(r => setTimeout(r, 140))
  }
  const durMs = Date.now() - t0
  await send('Page.stopScreencast')
  const times = frameTimes.slice()
  const iv = times.slice(1).map((t, i) => t - times[i])
  iv.sort((a, b) => a - b)
  const p = (q) => iv.length ? iv[Math.min(iv.length - 1, Math.floor(iv.length * q))] : -1
  const sum = iv.reduce((a, b) => a + b, 0)
  console.log(`${tag} | idle-fps~${(idleFrames / 0.8).toFixed(0)}  scroll: frames=${times.length} fps=${(times.length / (durMs / 1000)).toFixed(1)} p50=${p(0.5)}ms p95=${p(0.95)}ms max=${iv[iv.length - 1]}ms`)
}

for (const cfg of ['A', 'B', 'C']) {
  await setTest(CFG[cfg])
  await new Promise(r => setTimeout(r, 600))
  await scrollTest(`cfg ${cfg}`)
}
await setTest('')
await evalv(`document.getElementById('wb-scroll-test')?.remove(); document.documentElement.setAttribute('data-renderer-animations-paused',''); 'done'`)
console.log('done')
process.exit(0)
