// wb-style-bench.mjs — controlled style-recalc benchmark for streaming-like DOM bursts
// env: BENCH_MODE=on|off  (off => disable the field/contrib style elements first)
const port = Number(process.env.HERMES_DESKTOP_CDP_PORT || 9333)
const mode = process.env.BENCH_MODE || 'on'
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
// inventory style elements
const styles = await ev(`[...document.querySelectorAll('style')].map(s => ({ id: s.id || '', n: s.textContent.length, head: s.textContent.slice(0, 60).replace(/\\s+/g, ' '), field: s.textContent.includes('data-contrib-shell') }))`)
console.log('style elements:', JSON.stringify(styles, null, 1))
if (mode === 'off') {
  const dis = await ev(`(() => { let n = 0; for (const s of document.querySelectorAll('style')) { if (s.textContent.includes('data-contrib-shell')) { s.disabled = true; n++ } } return n })()`)
  console.log('disabled field styles:', dis)
} else {
  await ev(`(() => { for (const s of document.querySelectorAll('style')) { if (s.textContent.includes('data-contrib-shell')) { s.disabled = false } } return 1 })()`)
}
// install bench host
await ev(`(() => {
  const old = document.getElementById('__wb_bench_host')
  if (old) old.remove()
  const host = document.createElement('div')
  host.id = '__wb_bench_host'
  host.style.cssText = 'position:fixed;left:8px;bottom:8px;width:340px;height:130px;overflow:hidden;opacity:0.01;pointer-events:none;z-index:1'
  const content = document.createElement('div')
  host.appendChild(content)
  document.body.appendChild(host)
  window.__wbBench = { host, content, burst: 0 }
  return 'bench-host-added'
})()`)
let prev = await metrics()
const t0 = await metrics()
let totalMut = 0
for (let i = 1; i <= 150; i++) {
  const n = await ev(`(() => {
    const b = window.__wbBench
    b.burst++
    const p = document.createElement('p')
    p.className = 'wrap-anywhere'
    p.textContent = 'streaming token cluster number ' + b.burst + ' with some words to wrap'
    b.content.appendChild(p)
    if (b.content.childNodes.length > 60) b.content.removeChild(b.content.firstChild)
    return b.burst
  })()`)
  totalMut++
  if (i % 25 === 0) {
    const cur = await metrics()
    const d = (k) => (cur[k] || 0) - (prev[k] || 0)
    console.log(`bursts=${i} style=+${d('RecalcStyleDuration').toFixed(3)}s script=+${d('ScriptDuration').toFixed(3)}s task=+${d('TaskDuration').toFixed(3)}s layout=+${d('LayoutDuration').toFixed(3)}s`)
    prev = cur
  }
}
const cur = await metrics()
const dTotal = (k) => (cur[k] || 0) - (t0[k] || 0)
console.log(`TOTAL[${mode}] style=${dTotal('RecalcStyleDuration').toFixed(3)}s script=${dTotal('ScriptDuration').toFixed(3)}s task=${dTotal('TaskDuration').toFixed(3)}s layout=${dTotal('LayoutDuration').toFixed(3)}s`)
await ev(`(() => { const h = document.getElementById('__wb_bench_host'); if (h) h.remove(); return 'cleaned' })()`)
if (mode === 'off') await ev(`(() => { for (const s of document.querySelectorAll('style')) { if (s.textContent.includes('data-contrib-shell')) s.disabled = false } return 'reenabled' })()`)
process.exit(0)
