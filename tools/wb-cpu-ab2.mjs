// Decisive A/B: process CPU burn with the field animating vs static vs hidden.
import { execSync } from 'node:child_process'
const port = Number(process.env.HERMES_DESKTOP_CDP_PORT || 9333)
const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json()
const main = targets.find((t) => t.type === 'page' && (t.url || '').startsWith('file://'))
const ws = new WebSocket(main.webSocketDebuggerUrl)
let id = 0
const pending = new Map()
ws.addEventListener('message', (ev) => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id) } })
await new Promise((r) => ws.addEventListener('open', r))
const send = (method, params, timeoutMs = 60000) => new Promise((res) => {
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
const setTest = (css) => evalv(`(() => { let el = document.getElementById('wb-cpu-test'); if (!el) { el = document.createElement('style'); el.id = 'wb-cpu-test'; document.head.appendChild(el); } el.textContent = ${JSON.stringify(css)}; return 'ok' })()`)

const sample = (tag) => {
  const out = execSync('powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:/Users/<用户名>/Desktop/hermes-agent-main/.build/workbench/wb-cpu-sample.ps1', { encoding: 'utf8', timeout: 30000 })
  console.log(tag.padEnd(26), out.trim())
}

// hold animations ON (simulate user looking at the app)
await evalv(`document.documentElement.removeAttribute('data-renderer-animations-paused'); 'x'`)
await new Promise(r => setTimeout(r, 400))

await sample('A) field ANIMATING')
await setTest(`:root:has([data-contrib-shell])::before,:root:has([data-contrib-shell])::after,:root:has([data-contrib-shell]) body::after{animation:none !important}`)
await sample('B) field STATIC (layers on)')
await setTest(`:root:has([data-contrib-shell])::before,:root:has([data-contrib-shell])::after,:root:has([data-contrib-shell]) body::after{display:none !important}`)
await sample('C) field HIDDEN (baseline)')
await setTest('')
await evalv(`document.getElementById('wb-cpu-test')?.remove(); 'cleanup'`)
console.log('done')
process.exit(0)
