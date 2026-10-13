// Live pacing comparison now that the window seems active: field animating vs hidden.
const port = Number(process.env.HERMES_DESKTOP_CDP_PORT || 9333)
const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json()
const main = targets.find((t) => t.type === 'page' && (t.url || '').startsWith('file://'))
const ws = new WebSocket(main.webSocketDebuggerUrl)
let id = 0
const pending = new Map()
ws.addEventListener('message', (ev) => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id) } })
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

const SAMPLE = (ms) => `(async () => {
  const pts = []
  const t0 = performance.now()
  await new Promise((done) => {
    let n = 0
    const tick = (now) => { pts.push(now); if (++n >= 400 || now - t0 > ${ms}) return done(); requestAnimationFrame(tick) }
    requestAnimationFrame(tick)
    setTimeout(done, ${ms} + 400)
  })
  const ds = pts.slice(1).map((v, i) => v - pts[i]).filter(d => d > 0)
  if (!ds.length) return { frames: 0 }
  ds.sort((a, b) => a - b)
  const p = (q) => +ds[Math.min(ds.length - 1, Math.floor(ds.length * q))].toFixed(1)
  const sum = ds.reduce((a, b) => a + b, 0)
  return { frames: ds.length + 1, effFps: +((ds.length + 1) / (sum / 1000)).toFixed(1), p50: p(0.5), p90: p(0.9), max: +ds[ds.length - 1].toFixed(1), over33: ds.filter(d => d > 33).length }
})()`

console.log('pausedAttr:', await evalv(`document.documentElement.hasAttribute('data-renderer-animations-paused')`), '| hidden:', await evalv('document.hidden'), '| focus:', await evalv('document.hasFocus()'))
console.log('A) field ANIMATING :', JSON.stringify(await evalv(SAMPLE(3500))))
const setTest = (css) => evalv(`(() => { let el = document.getElementById('wb-perf-test2'); if (!el) { el = document.createElement('style'); el.id = 'wb-perf-test2'; document.head.appendChild(el); } el.textContent = ${JSON.stringify(css)}; return 'ok' })()`)
await setTest(`:root:has([data-contrib-shell])::before,:root:has([data-contrib-shell])::after,:root:has([data-contrib-shell]) body::after{display:none !important}`)
console.log('B) field HIDDEN    :', JSON.stringify(await evalv(SAMPLE(3500))))
await evalv(`document.getElementById('wb-perf-test2')?.remove(); 'ok'`)
console.log('cleanup ok')
process.exit(0)
