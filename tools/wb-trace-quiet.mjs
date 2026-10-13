// wb-trace-quiet.mjs — 5s renderer trace with NO state manipulation (observe as-is)
const port = Number(process.env.HERMES_DESKTOP_CDP_PORT || 9333)
const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json()
const main = targets.find((t) => t.type === 'page' && (t.url || '').startsWith('file://'))
const ws = new WebSocket(main.webSocketDebuggerUrl)
let id = 0
const pending = new Map()
const traceEvents = []
ws.addEventListener('message', (ev) => {
  const m = JSON.parse(ev.data)
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id) }
  else if (m.method === 'Tracing.dataCollected') traceEvents.push(...(m.params.value || []))
})
await new Promise((r) => ws.addEventListener('open', r))
const send = (method, params, timeoutMs = 30000) => new Promise((res) => {
  const i = ++id
  pending.set(i, res)
  ws.send(JSON.stringify({ id: i, method, params }))
  setTimeout(() => { if (pending.has(i)) { pending.delete(i); res({ __timeout: method }) } }, timeoutMs)
})
await send('Tracing.start', {
  categories: 'devtools.timeline,blink.animations,cc,benchmark,disabled-by-default-devtools.timeline',
  transferMode: 'ReportEvents'
})
await new Promise((r) => setTimeout(r, 5000))
await send('Tracing.end')
await new Promise((r) => setTimeout(r, 1500))
const byName = new Map()
for (const e of traceEvents) {
  if (e.ph !== 'X') continue
  const rec = byName.get(e.name) || { count: 0, dur: 0 }
  rec.count++
  rec.dur += e.dur || 0
  byName.set(e.name, rec)
}
const top = [...byName.entries()].sort((a, b) => b[1].dur - a[1].dur).slice(0, 22)
console.log('total trace events:', traceEvents.length)
console.log('name'.padEnd(46), 'count'.padStart(7), 'totalDur(ms)'.padStart(12))
for (const [name, rec] of top) {
  console.log(name.slice(0, 45).padEnd(46), String(rec.count).padStart(7), (rec.dur / 1000).toFixed(1).padStart(12))
}
process.exit(0)
