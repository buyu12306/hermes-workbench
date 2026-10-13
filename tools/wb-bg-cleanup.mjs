// Remove the test style and verify the field still resolves from the skin CSS alone.
const port = Number(process.env.HERMES_DESKTOP_CDP_PORT || 9333)
const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json()
const main = targets.find((t) => t.type === 'page' && (t.url || '').startsWith('file://'))
const ws = new WebSocket(main.webSocketDebuggerUrl)
let id = 0
const pending = new Map()
ws.addEventListener('message', (ev) => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id) } })
await new Promise((r) => ws.addEventListener('open', r))
const send = (method, params, timeoutMs = 15000) => new Promise((res) => {
  const i = ++id
  pending.set(i, res)
  ws.send(JSON.stringify({ id: i, method, params }))
  setTimeout(() => { if (pending.has(i)) { pending.delete(i); res({ __timeout: method }) } }, timeoutMs)
})
const evalv = async (expression) => (await send('Runtime.evaluate', { expression, returnByValue: true })).result?.result?.value
console.log('remove:', await evalv(`document.getElementById('wb-bg-test')?.remove(); !!document.getElementById('wb-bg-test')`))
const r = await evalv(`(() => {
  const g = (el, pe) => { const cs = getComputedStyle(el, pe); return cs.animationName + ' / ' + cs.animationPlayState }
  return {
    testGone: !document.getElementById('wb-bg-test'),
    skinCss: !!document.getElementById('hermes-desktop-custom-css'),
    field: g(document.documentElement, '::before'),
    far: g(document.documentElement, '::after'),
    near: g(document.body, '::before'),
    shooter: g(document.body, '::after')
  }
})()`)
console.log(JSON.stringify(r, null, 1))
process.exit(0)
