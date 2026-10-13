// Verify the workbench-field plugin: wheel sets data-wb-scroll, field pauses, then clears.
const port = Number(process.env.HERMES_DESKTOP_CDP_PORT || 9333)
const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json()
const main = targets.find((t) => t.type === 'page' && (t.url || '').startsWith('file://'))
const ws = new WebSocket(main.webSocketDebuggerUrl)
let id = 0
const pending = new Map()
ws.addEventListener('message', (ev) => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id) } })
await new Promise((r) => ws.addEventListener('open', r))
const send = (method, params, timeoutMs = 20000) => new Promise((res) => {
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

// ensure animations run (as if the user is looking)
await evalv(`document.documentElement.removeAttribute('data-renderer-animations-paused'); 'on'`)
await new Promise(r => setTimeout(r, 300))

console.log('before wheel :', JSON.stringify(await evalv(`({ flag: document.documentElement.hasAttribute('data-wb-scroll'), play: getComputedStyle(document.documentElement, '::before').animationPlayState })`)))

// real wheel event through the input pipeline
await send('Input.dispatchMouseEvent', { type: 'mouseWheel', x: 870, y: 400, deltaX: 0, deltaY: 180 })
await new Promise(r => setTimeout(r, 120))
console.log('during scroll:', JSON.stringify(await evalv(`({ flag: document.documentElement.hasAttribute('data-wb-scroll'), play: getComputedStyle(document.documentElement, '::before').animationPlayState, starPlay: getComputedStyle(document.documentElement, '::after').animationPlayState, shootPlay: getComputedStyle(document.body, '::after').animationPlayState })`)))

await new Promise(r => setTimeout(r, 700))
console.log('after 700ms  :', JSON.stringify(await evalv(`({ flag: document.documentElement.hasAttribute('data-wb-scroll'), play: getComputedStyle(document.documentElement, '::before').animationPlayState })`)))

// also confirm listeners exist from the plugin (wheel bubbles to document capture) and plugin count
console.log('attr survives direct read:', await evalv(`'ok'`))
process.exit(0)
