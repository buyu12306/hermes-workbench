// Cost matrix for the workbench field, measured with the window frontmost.
// Configs: A field animating (as shipped) | B field animating, backdrop-filter off
//          C field static | D field layers hidden (pre-field baseline)
// Reports rAF frame pacing + main-thread task metrics per config.
const port = Number(process.env.HERMES_DESKTOP_CDP_PORT || 9333)
const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json()
const main = targets.find((t) => t.type === 'page' && (t.url || '').startsWith('file://'))
const ws = new WebSocket(main.webSocketDebuggerUrl)
let id = 0
const pending = new Map()
ws.addEventListener('message', (ev) => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id) } })
await new Promise((r) => ws.addEventListener('open', r))
const send = (method, params, timeoutMs = 30000) => new Promise((res) => {
  const i = ++id
  pending.set(i, res)
  ws.send(JSON.stringify({ id: i, method, params }))
  setTimeout(() => { if (pending.has(i)) { pending.delete(i); res({ __timeout: method }) } }, timeoutMs)
})
const evalv = async (expression) => (await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })).result?.result?.value

await send('Page.bringToFront')
await new Promise((r) => setTimeout(r, 1200))
console.log('focus check: hasFocus =', await evalv('document.hasFocus()'), '| visible =', await evalv('document.visibilityState'))

const setTest = (css) => evalv(`(() => { let el = document.getElementById('wb-perf-test'); if (!el) { el = document.createElement('style'); el.id='wb-perf-test'; document.head.appendChild(el); } el.textContent = ${JSON.stringify(css)}; return 'ok' })()`)

const RUN = (ms) => `(async () => {
  const html = document.documentElement
  html.removeAttribute('data-renderer-animations-paused')
  await new Promise(r => setTimeout(r, 400))
  const ensure = () => html.removeAttribute('data-renderer-animations-paused')
  const pts = []
  const t0 = performance.now()
  await new Promise((done) => {
    let n = 0
    const tick = (now) => {
      pts.push(now)
      ensure()
      if (++n >= 240 || now - t0 > ${ms}) return done()
      requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)
    setTimeout(done, ${ms})
  })
  const deltas = pts.slice(1).map((v, i) => v - pts[i]).filter(d => d > 0 && d < 2000)
  deltas.sort((a, b) => a - b)
  if (!deltas.length) return { frames: 0 }
  const p = (q) => deltas[Math.min(deltas.length - 1, Math.floor(deltas.length * q))]
  const sum = deltas.reduce((a, b) => a + b, 0)
  const out = { frames: deltas.length, effFps: +(1000 / (sum / deltas.length)).toFixed(1), p50: +p(0.5).toFixed(1), p90: +p(0.9).toFixed(1), p99: +p(0.99).toFixed(1), over25: deltas.filter(d => d > 25).length, over50: deltas.filter(d => d > 50).length }
  html.setAttribute('data-renderer-animations-paused', '')
  return out
})()`

const METRIC = `(async () => { if (!window.__wbPerf) window.__wbPerf = {}; return 1 })()`

const metrics = async () => {
  const r = await send('Performance.enable')
  const m = await send('Performance.getMetrics')
  const get = (n) => { const e = m.result?.metrics?.find(x => x.name === n); return e ? e.value : -1 }
  return { TaskDuration: get('TaskDuration'), ScriptDuration: get('ScriptDuration'), RecalcStyleDuration: get('RecalcStyleDuration'), LayoutDuration: get('LayoutDuration') }
}

const label = async (tag, css) => {
  await setTest(css)
  const m0 = await metrics()
  const pacing = await evalv(RUN(4500))
  const m1 = await metrics()
  const d = (k) => +(m1[k] - m0[k]).toFixed(3)
  console.log(`${tag} : ${JSON.stringify(pacing)} | main-thread: task +${d('TaskDuration')}s script +${d('ScriptDuration')}s style +${d('RecalcStyleDuration')}s layout +${d('LayoutDuration')}s`)
}

const KILL_ANIM = `:root:has([data-contrib-shell])::before,:root:has([data-contrib-shell])::after,:root:has([data-contrib-shell]) body::before,:root:has([data-contrib-shell]) body::after{animation:none !important}`
const KILL_LAYERS = `:root:has([data-contrib-shell])::before,:root:has([data-contrib-shell])::after,:root:has([data-contrib-shell]) body::before,:root:has([data-contrib-shell]) body::after{display:none !important}`
const KILL_FROST = `*,*::before,*::after{backdrop-filter:none !important;-webkit-backdrop-filter:none !important}`

await label('A animating (shipped)      ', '')
await label('B animating, frost off     ', KILL_FROST)
await label('C static field, frost on   ', KILL_ANIM)
await label('D field hidden (baseline)  ', KILL_LAYERS)

// cleanup
await evalv(`document.getElementById('wb-perf-test')?.remove(); document.documentElement.setAttribute('data-renderer-animations-paused',''); 'ok'`)
console.log('cleanup ok')
process.exit(0)
