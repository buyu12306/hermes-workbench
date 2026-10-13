// Keydown flag diagnostics: synthetic event vs CDP key event.
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

const flagNow = () => evalv(`({ flag: document.documentElement.hasAttribute('data-wb-scroll'), play: getComputedStyle(document.documentElement, '::before').animationPlayState })`)

// 1) wheel sanity
await evalv(`document.documentElement.removeAttribute('data-wb-scroll'); 'x'`)
await send('Input.dispatchMouseEvent', { type: 'mouseWheel', x: 870, y: 400, deltaX: 0, deltaY: 120 })
await new Promise(r => setTimeout(r, 120))
console.log('after wheel  :', JSON.stringify(await flagNow()))
await new Promise(r => setTimeout(r, 700))

// 2) synthetic keydown (tests the plugin listener directly)
console.log('synthetic kd :', JSON.stringify(await evalv(`(() => { document.dispatchEvent(new KeyboardEvent('keydown', { key: 'PageDown', bubbles: true, cancelable: true })); return { flag: document.documentElement.hasAttribute('data-wb-scroll') } })()`)))
await new Promise(r => setTimeout(r, 700))

// 3) CDP key events with fuller params
await send('Input.dispatchKeyEvent', { type: 'rawKeyDown', key: 'PageDown', code: 'PageDown', windowsVirtualKeyCode: 34, nativeVirtualKeyCode: 34 })
await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'PageDown', code: 'PageDown', windowsVirtualKeyCode: 34, nativeVirtualKeyCode: 34 })
await new Promise(r => setTimeout(r, 150))
console.log('after rawKey :', JSON.stringify(await flagNow()))
await new Promise(r => setTimeout(r, 700))

// 4) plugin file mtime vs now (did the edit land?)
process.exit(0)
