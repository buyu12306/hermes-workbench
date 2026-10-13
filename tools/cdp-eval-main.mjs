// Eval an expression against the MAIN Hermes window target (not preview/webview pages).
const port = Number(process.env.HERMES_DESKTOP_CDP_PORT || 9333)
const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json()
const main = targets.find((t) => t.type === 'page' && (t.url || '').startsWith('file://'))
  || targets.find((t) => t.type === 'page' && t.title === 'Hermes')
if (!main) { console.error('no main target; targets:', targets.map(t => t.url).join(' | ')); process.exit(1) }
const ws = new WebSocket(main.webSocketDebuggerUrl)
let id = 0
const pending = new Map()
ws.addEventListener('message', (ev) => { const m = JSON.parse(ev.data); if (pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id) } })
await new Promise((r) => ws.addEventListener('open', r))
const send = (method, params, timeoutMs = 15000) => new Promise((res) => {
  const i = ++id
  pending.set(i, res)
  ws.send(JSON.stringify({ id: i, method, params }))
  setTimeout(() => { if (pending.has(i)) { pending.delete(i); res({ __timeout: method }) } }, timeoutMs)
})
const expr = process.argv[2] || '1+1'
const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true })
if (r.__timeout) { console.error('EVAL TIMEOUT'); process.exit(2) }
if (r.result && r.result.exceptionDetails) {
  console.error('EXCEPTION:', r.result.exceptionDetails.exception?.description || JSON.stringify(r.result.exceptionDetails).slice(0, 300))
} else {
  console.log(JSON.stringify(r.result && r.result.result ? r.result.result.value : r, null, 1))
}
process.exit(0)
