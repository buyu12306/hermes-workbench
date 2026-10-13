// Capture a screenshot of the app via CDP.
const port = Number(process.env.HERMES_DESKTOP_CDP_PORT || 9333)
const out = process.argv[2] || 'shot.png'
const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json()
const t = targets.find((t) => t.type === 'page')
if (!t) { console.error('no page target'); process.exit(1) }
const ws = new WebSocket(t.webSocketDebuggerUrl)
let id = 0
const pending = new Map()
ws.addEventListener('message', (ev) => { const m = JSON.parse(ev.data); if (pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id) } })
await new Promise((r) => ws.addEventListener('open', r))
const send = (method, params) => new Promise((res) => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })) })
const r = await send('Page.captureScreenshot', { format: 'png' })
if (r.result && r.result.data) {
  const fs = await import('node:fs')
  fs.writeFileSync(out, Buffer.from(r.result.data, 'base64'))
  console.log('saved', out)
} else {
  console.error('capture failed', JSON.stringify(r).slice(0, 300))
}
ws.close()
