// screenshot v3: list targets, bring window to front, restore if minimized, capture 30s.
const port = Number(process.env.HERMES_DESKTOP_CDP_PORT || 9333)
const out = process.argv[2] || 'shot3.png'
const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json()
console.log('targets:', targets.map(t => `${t.type}:${t.title || ''}:${(t.url || '').slice(0, 60)}`).join(' | '))
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
const send = (method, params, timeoutMs = 30000) => new Promise((res) => {
  const i = ++id
  pending.set(i, res)
  ws.send(JSON.stringify({ id: i, method, params }))
  setTimeout(() => { if (pending.has(i)) { pending.delete(i); res({ __timeout: method }) } }, timeoutMs)
})
await send('Page.enable')
await send('Page.bringToFront')
const win = await send('Browser.getWindowForTarget', { targetId: t.id })
console.log('window:', JSON.stringify(win.result || win.__timeout || win).slice(0, 200))
if (win.result && win.result.windowId != null && (win.result.bounds && win.result.bounds.windowState !== 'normal')) {
  const r = await send('Browser.setWindowBounds', { windowId: win.result.windowId, bounds: { windowState: 'normal' } })
  console.log('setWindowBounds:', JSON.stringify(r.result || r.__timeout || r).slice(0, 120))
  await new Promise(r => setTimeout(r, 1200))
}
const r = await send('Page.captureScreenshot', { format: 'png' })
const fs = await import('node:fs')
if (!r.__timeout && r.result && r.result.data) {
  fs.writeFileSync(out, Buffer.from(r.result.data, 'base64'))
  console.log('saved', out, fs.statSync(out).size, 'bytes')
} else {
  console.error('capture failed/timeout:', JSON.stringify(r).slice(0, 200))
  const r2 = await send('Page.captureScreenshot', { format: 'png', fromSurface: false })
  if (r2.result && r2.result.data) {
    fs.writeFileSync(out, Buffer.from(r2.result.data, 'base64'))
    console.log('saved (fallback)', out, fs.statSync(out).size, 'bytes')
  }
}
process.exit(0)
