// Inject (or replace) the test background <style> in the live main window.
// Usage: node wb-bg-inject.mjs <css-file> [styleId]
const fs = await import('node:fs')
const port = Number(process.env.HERMES_DESKTOP_CDP_PORT || 9333)
const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json()
const main = targets.find((t) => t.type === 'page' && (t.url || '').startsWith('file://'))
if (!main) { console.error('no main target'); process.exit(1) }
const ws = new WebSocket(main.webSocketDebuggerUrl)
let id = 0
const pending = new Map()
ws.addEventListener('message', (ev) => { const m = JSON.parse(ev.data); if (pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id) } })
await new Promise((r) => ws.addEventListener('open', r))
const send = (method, params, timeoutMs = 20000) => new Promise((res) => {
  const i = ++id
  pending.set(i, res)
  ws.send(JSON.stringify({ id: i, method, params }))
  setTimeout(() => { if (pending.has(i)) { pending.delete(i); res({ __timeout: method }) } }, timeoutMs)
})

const css = fs.readFileSync(process.argv[2], 'utf8')
const styleId = process.argv[3] || 'wb-bg-test'
const expr = `(() => {
  const id = ${JSON.stringify(styleId)};
  let el = document.getElementById(id);
  if (!el) { el = document.createElement('style'); el.id = id; document.head.appendChild(el); }
  el.textContent = ${JSON.stringify(css)};
  return { id, bytes: el.textContent.length, present: !!document.getElementById(id) };
})()`
const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true })
console.log(JSON.stringify(r.result?.result?.value ?? r, null, 1))
process.exit(0)
