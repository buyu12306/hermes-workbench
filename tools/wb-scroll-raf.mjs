// Definitive in-page scroll probe: rAF cadence + data-wb-scroll flag timeline + wheel count.
// Configs: A as-shipped | D layers visible but animation:none | B layers hidden.
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
const setTest = (css) => evalv(`(() => { let el = document.getElementById('wb-scroll-test'); if (!el) { el = document.createElement('style'); el.id = 'wb-scroll-test'; document.head.appendChild(el); } el.textContent = ${JSON.stringify(css)}; return 'ok' })()`)

const G = ':root:has([data-contrib-shell]):not(:has([data-hud-shell]))'
const CFG = {
  A: '',
  D: `${G}::before,${G}::after,${G} body::after{animation:none !important}`,
  B: `${G}::before,${G}::after,${G} body::after{display:none !important}`
}

const SETUP = `(() => {
  window.__sp = { on: false, wheels: 0, flagEvents: [], rafIv: [], t0: 0 }
  window.__spWheel = () => { window.__sp.wheels++ }
  document.addEventListener('wheel', window.__spWheel, { capture: true, passive: true })
  window.__spMo = new MutationObserver(() => {
    window.__sp.flagEvents.push([Math.round(performance.now() - window.__sp.t0), document.documentElement.hasAttribute('data-wb-scroll')])
  })
  window.__spMo.observe(document.documentElement, { attributes: true, attributeFilter: ['data-wb-scroll'] })
  window.__spTick = (now) => {
    if (!window.__sp.on) return
    window.__sp.rafIv.push(Math.round(now - window.__sp.last))
    window.__sp.last = now
    requestAnimationFrame(window.__spTick)
  }
  return 'setup'
})()`

const START = `(() => { const s = window.__sp; s.on = true; s.t0 = performance.now(); s.last = performance.now(); s.rafIv = []; requestAnimationFrame(window.__spTick); return 'started' })()`
const STOP = `(() => {
  const s = window.__sp
  s.on = false
  const iv = s.rafIv.slice().sort((a, b) => a - b)
  const p = (q) => iv.length ? iv[Math.min(iv.length - 1, Math.floor(iv.length * q))] : -1
  const flagOnCount = s.flagEvents.filter(e => e[1]).length
  return { wheels: s.wheels, rafFrames: iv.length, rafP50: p(0.5), rafP95: p(0.95), rafMax: iv[iv.length - 1], flagToggles: s.flagEvents.length, flagOn: flagOnCount }
})()`

await evalv(SETUP)
await evalv(`document.documentElement.removeAttribute('data-renderer-animations-paused'); 'on'`)
for (const cfg of ['A', 'D', 'B']) {
  await setTest(CFG[cfg])
  await new Promise(r => setTimeout(r, 600))
  await evalv(`(() => { const s = document.querySelector('[data-slot="aui_thread-viewport"]'); s.scrollTop = Math.max(0, Math.round(s.scrollHeight * 0.4)); window.__sp.wheels = 0; window.__sp.flagEvents = []; return 1 })()`)
  await evalv(START)
  const t0 = Date.now()
  for (let i = 0; i < 22; i++) {
    await send('Input.dispatchMouseEvent', { type: 'mouseWheel', x: 870, y: 400, deltaX: 0, deltaY: i < 11 ? 260 : -260 })
    await new Promise(r => setTimeout(r, 120))
  }
  const wall = Date.now() - t0
  const res = await evalv(STOP)
  console.log(`cfg ${cfg} | wall=${wall}ms wheels=${res.wheels} rafFrames=${res.rafFrames} p50=${res.rafP50} p95=${res.rafP95} max=${res.rafMax} | flagToggles=${res.flagToggles} flagOn=${res.flagOn}`)
}
await evalv(`document.getElementById('wb-spWheel')?.remove; document.removeEventListener('wheel', window.__spWheel, true); window.__spMo?.disconnect(); document.getElementById('wb-scroll-test')?.remove(); document.documentElement.setAttribute('data-renderer-animations-paused',''); 'done'`)
console.log('done')
process.exit(0)
