// Capture a screenshot via CDP with a hard timeout and raw diagnostics.
const port = Number(process.env.HERMES_DESKTOP_CDP_PORT || 9333)
const out = process.argv[2] || 'shot.png'
const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json()
const t = targets.find((t) => t.type === 'page' && (t.url || '').startsWith('file://'))
  || targets.find((t) => t.type === 'page' && t.title === 'Hermes')
if (!t) { console.error('no main target'); process.exit(1) }
const ws = new WebSocket(t.webSocketDebuggerUrl)
let id = 0
const pending = new Map()
ws.addEventListener('message', (ev) => {
  const m = JSON.parse(ev.data)
  if (pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id) }
})
await new Promise((r) => ws.addEventListener('open', r))
const send = (method, params, timeoutMs = 12000) => new Promise((res) => {
  const i = ++id
  pending.set(i, res)
  ws.send(JSON.stringify({ id: i, method, params }))
  setTimeout(() => { if (pending.has(i)) { pending.delete(i); res({ __timeout: method }) } }, timeoutMs)
})
const r = await send('Page.captureScreenshot', { format: 'png' })
if (r.__timeout) {
  console.error('TIMEOUT capturing screenshot; trying with fromSurface:false...')
  const r2 = await send('Page.captureScreenshot', { format: 'png', fromSurface: false, captureBeyondViewport: false })
  if (r2.result && r2.result.data) {
    const fs = await import('node:fs')
    fs.writeFileSync(out, Buffer.from(r2.result.data, 'base64'))
    console.log('saved (fallback)', out)
  } else {
    console.error('fallback failed', JSON.stringify(r2).slice(0, 300))
  }
} else if (r.result && r.result.data) {
  const fs = await import('node:fs')
  fs.writeFileSync(out, Buffer.from(r.result.data, 'base64'))
  console.log('saved', out)
} else {
  console.error('capture failed', JSON.stringify(r).slice(0, 300))
}
process.exit(0)
