// wb-stream-probe.mjs — 4 min: main-thread metrics + DOM mutation rate + window state
const port = Number(process.env.HERMES_DESKTOP_CDP_PORT || 9333)
const durMs = Number(process.env.PROBE_MS || 240000)
const stepMs = Number(process.env.PROBE_STEP || 12000)
const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json()
const main = targets.find((t) => t.type === 'page' && (t.url || '').startsWith('file://'))
const ws = new WebSocket(main.webSocketDebuggerUrl)
let id = 0
const pending = new Map()
ws.addEventListener('message', (ev) => {
  const m = JSON.parse(ev.data)
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id) }
})
await new Promise((r) => ws.addEventListener('open', r))
const send = (method, params) => new Promise((res) => {
  const i = ++id
  pending.set(i, res)
  ws.send(JSON.stringify({ id: i, method, params }))
})
const ev = async (expression) => {
  const r = await send('Runtime.evaluate', { expression, returnByValue: true })
  return r.result && r.result.result ? r.result.result.value : null
}
const metrics = async () => {
  const r = await send('Performance.getMetrics')
  const o = {}
  for (const m of (r.result ? r.result.metrics : [])) o[m.name] = m.value
  return o
}
await send('Performance.enable')
await ev(`(() => {
  if (window.__wbMut) return 'already'
  window.__wbMut = { total: 0, byTarget: {}, byType: {} }
  const obs = new MutationObserver(ms => {
    const w = window.__wbMut
    for (const m of ms) {
      w.total++
      w.byType[m.type] = (w.byType[m.type] || 0) + 1
      const t = m.target
      const el = t && t.nodeType === 1 ? t : (t && t.parentElement)
      if (el) {
        const c = el.className
        const cn = (typeof c === 'string') ? c : ((c && c.baseVal) || '')
        const key = ((t.nodeType === 1 ? '' : 'text@') + el.tagName + '.' + cn).slice(0, 64)
        w.byTarget[key] = (w.byTarget[key] || 0) + 1
      }
    }
  })
  obs.observe(document.documentElement, { subtree: true, childList: true, characterData: true, attributes: true })
  return 'installed'
})()`)
let prev = await metrics()
let prevMut = 0
const t0 = Date.now()
while (Date.now() - t0 < durMs) {
  await new Promise((r) => setTimeout(r, stepMs))
  const cur = await metrics()
  const mut = await ev(`(() => { const w = window.__wbMut; return { total: w.total, byType: w.byType, topT: Object.entries(w.byTarget).sort((a, b) => b[1] - a[1]).slice(0, 6) } })()`)
  const st = await ev(`JSON.stringify({h:(location.hash||'').slice(-12),focus:document.hasFocus(),idle:document.documentElement.hasAttribute('data-wb-idle'),p:document.documentElement.getAttribute('data-renderer-animations-paused')})`)
  const d = (k) => ((cur[k] || 0) - (prev[k] || 0)).toFixed(3)
  const dmut = mut ? (mut.total - prevMut) : '?'
  if (mut) prevMut = mut.total
  console.log(`${new Date().toTimeString().slice(0, 8)} task=+${d('TaskDuration')}s script=+${d('ScriptDuration')}s layout=+${d('LayoutDuration')}s style=+${d('RecalcStyleDuration')}s | domMut=+${dmut} | ${st} | top=${mut ? JSON.stringify(mut.topT) : ''}`)
  prev = cur
}
process.exit(0)
