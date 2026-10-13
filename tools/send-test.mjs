// End-to-end test: type a message into the live workbench composer and send it
// via CDP (real user-like input), then report the composer state.
const port = Number(process.env.HERMES_DESKTOP_CDP_PORT || 9333)
const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json()
const t = targets.find((t) => t.type === 'page')
if (!t) { console.error('no page target'); process.exit(1) }
const ws = new WebSocket(t.webSocketDebuggerUrl)
let id = 0
const pending = new Map()
ws.addEventListener('message', (ev) => { const m = JSON.parse(ev.data); if (pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id) } })
await new Promise((r) => ws.addEventListener('open', r))
const send = (method, params) => new Promise((res) => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })) })
const evalJs = async (expr) => (await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true })).result?.result?.value
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

await evalJs(`document.querySelector('[data-slot="composer-rich-input"]').focus()`)
await sleep(300)
await send('Input.insertText', { text: process.env.TEST_MESSAGE || '工作台端到端测试：你好！' })
await sleep(600)
console.log('composer after typing:', JSON.stringify(await evalJs(`document.querySelector('[data-slot="composer-rich-input"]').innerText`)))
// find a send button that may have appeared
console.log('buttons now:', JSON.stringify(await evalJs(`[...document.querySelectorAll('button')].map(b=>b.getAttribute('aria-label')).filter(Boolean).filter(a=>/send|发送|submit/i.test(a)).slice(0,5)`)))
for (const type of ['keyDown', 'keyUp']) {
  await send('Input.dispatchKeyEvent', { type, key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, nativeVirtualKeyCode: 13 })
}
await sleep(1800)
console.log('composer after Enter:', JSON.stringify(await evalJs(`document.querySelector('[data-slot="composer-rich-input"]')?.innerText ?? '<gone>'`)))
ws.close()
