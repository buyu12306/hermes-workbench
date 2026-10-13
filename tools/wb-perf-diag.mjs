// Perf diagnosis for the dynamic field:
// A) detect leftover animation playback-rate inflation
// B) rAF pacing + main-thread metrics in 3 configs (field animating / field static / field hidden)
const port = Number(process.env.HERMES_DESKTOP_CDP_PORT || 9333)
const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json()
const main = targets.find((t) => t.type === 'page' && (t.url || '').startsWith('file://'))
const ws = new WebSocket(main.webSocketDebuggerUrl)
let id = 0
const pending = new Map()
ws.addEventListener('message', (ev) => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id) } })
await new Promise((r) => ws.addEventListener('open', r))
const send = (method, params, timeoutMs = 20000) => new Promise((res) => {
  const i = ++id
  pending.set(i, res)
  ws.send(JSON.stringify({ id: i, method, params }))
  setTimeout(() => { if (pending.has(i)) { pending.delete(i); res({ __timeout: method }) } }, timeoutMs)
})
const evalv = async (expression) => (await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })).result?.result?.value

// A) playback rate probe: compare animation currentTime advance vs wall clock
const RATE_PROBE = `(async () => {
  const html = document.documentElement
  const wasPaused = html.hasAttribute('data-renderer-animations-paused')
  html.removeAttribute('data-renderer-animations-paused')
  const a = html.getAnimations({ subtree: true }).find(x => x.animationName === 'wb-field-drift')
  const t0 = a ? Number(a.currentTime) : null
  const w0 = performance.now()
  await new Promise(r => setTimeout(r, 1500))
  const t1 = a ? Number(a.currentTime) : null
  const w1 = performance.now()
  if (wasPaused) html.setAttribute('data-renderer-animations-paused', '')
  return { animAdvanceMs: t1 - t0, wallMs: w1 - w0, ratio: (t1 - t0) / (w1 - w0), wasPaused }
})()`
console.log('A) playback-rate probe:', JSON.stringify(await evalv(RATE_PROBE)))
await send('Animation.enable')
await send('Animation.setPlaybackRate', { playbackRate: 1 })
console.log('A) setPlaybackRate(1) applied (idempotent)')

// B) rAF pacing sampler
const RAF_SAMPLE = (ms) => `(async () => {
  const html = document.documentElement
  html.removeAttribute('data-renderer-animations-paused')
  await new Promise(r => setTimeout(r, 300))
  const deltas = []
  await new Promise((done) => {
    let last = performance.now()
    const tick = (now) => {
      deltas.push(now - last)
      last = now
      if (now - deltas._start > ${ms}) return done()
      requestAnimationFrame(tick)
    }
    deltas._start = performance.now()
    requestAnimationFrame(tick)
  })
  const vals = deltas.slice(2).sort((a, b) => a - b)
  const p = (q) => vals[Math.min(vals.length - 1, Math.floor(vals.length * q))]
  const sum = vals.reduce((a, b) => a + b, 0)
  const over25 = vals.filter(v => v > 25).length
  const over50 = vals.filter(v => v > 50).length
  html.setAttribute('data-renderer-animations-paused', '')
  return { frames: vals.length, spanMs: Math.round(sum), avg: +(sum / vals.length).toFixed(2), p50: +p(0.5).toFixed(2), p95: +p(0.95).toFixed(2), max: +vals[vals.length - 1].toFixed(2), over25, over50, effFps: +(vals.length / (sum / 1000)).toFixed(1) }
})()`

console.log('B1) field ANIMATING  :', JSON.stringify(await evalv(RAF_SAMPLE(4000))))

// static field: kill animations of our pseudos only
const STATIC_CSS = `:root:has([data-contrib-shell])::before,:root:has([data-contrib-shell])::after,:root:has([data-contrib-shell]) body::before,:root:has([data-contrib-shell]) body::after{animation:none !important}`
const setTest = (css) => evalv(`(() => { let el = document.getElementById('wb-perf-test'); if (!el) { el = document.createElement('style'); el.id='wb-perf-test'; document.head.appendChild(el); } el.textContent = ${JSON.stringify(css)}; return 'ok' })()`)
await setTest(STATIC_CSS)
console.log('B2) field STATIC     :', JSON.stringify(await evalv(RAF_SAMPLE(4000))))

// field hidden entirely (baseline: no field layers at all)
await setTest(`:root:has([data-contrib-shell])::before,:root:has([data-contrib-shell])::after,:root:has([data-contrib-shell]) body::before,:root:has([data-contrib-shell]) body::after{display:none !important}`)
console.log('B3) field HIDDEN     :', JSON.stringify(await evalv(RAF_SAMPLE(4000))))

// restore
await setTest('')
await evalv(`document.getElementById('wb-perf-test')?.remove(); document.documentElement.setAttribute('data-renderer-animations-paused',''); 'restored'`)
console.log('done')
process.exit(0)
