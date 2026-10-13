// GPU A/B: how much of the Hermes GPU-process load is the field?
// Configs: P paused (app attr on, user-away state) | A animating (as shipped when visible)
//          S static (animation:none) | H hidden (layers display:none)
import { execSync } from 'node:child_process'
const port = Number(process.env.HERMES_DESKTOP_CDP_PORT || 9333)
const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json()
const main = targets.find((t) => t.type === 'page' && (t.url || '').startsWith('file://'))
const ws = new WebSocket(main.webSocketDebuggerUrl)
let id = 0
const pending = new Map()
ws.addEventListener('message', (ev) => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id) } })
await new Promise((r) => ws.addEventListener('open', r))
const send = (method, params, timeoutMs = 30000) => new Promise((res) => {
  const i = ++id
  pending.set(i, res)
  ws.send(JSON.stringify({ id: i, method, params }))
  setTimeout(() => { if (pending.has(i)) { pending.delete(i); res({ __timeout: method }) } }, timeoutMs)
})
const evalv = async (expression) => {
  const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
  if (r.result?.exceptionDetails) console.log('EXC:', (r.result.exceptionDetails.exception?.description || '').slice(0, 160))
  return r.result?.result?.value
}
const setTest = (css) => evalv(`(() => { let el = document.getElementById('wb-gpu-test'); if (!el) { el = document.createElement('style'); el.id = 'wb-gpu-test'; document.head.appendChild(el); } el.textContent = ${JSON.stringify(css)}; return 'ok' })()`)
const gpuSample = () => execSync('powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:/Users/<用户名>/Desktop/hermes-agent-main/.build/workbench/wb-gpu-sample.ps1', { encoding: 'utf8', timeout: 30000 }).trim()

const G = ':root:has([data-contrib-shell]):not(:has([data-hud-shell]))'
const CFG = {
  P: { css: '', pause: true },
  A: { css: '', pause: false },
  S: { css: `${G}::before,${G} body::after{animation:none !important}`, pause: false },
  H: { css: `${G}::before,${G} body::after{display:none !important}`, pause: false }
}

console.log('animations in page:', await evalv(`document.getAnimations().length`))
for (const cfg of ['P', 'A', 'S', 'H']) {
  const c = CFG[cfg]
  await setTest(c.css)
  if (c.pause) await evalv(`document.documentElement.setAttribute('data-renderer-animations-paused',''); 'p'`)
  else await evalv(`document.documentElement.removeAttribute('data-renderer-animations-paused'); 'a'`)
  await new Promise(r => setTimeout(r, 500))
  console.log(`=== cfg ${cfg} ===`)
  console.log(gpuSample())
}
await setTest('')
await evalv(`document.getElementById('wb-gpu-test')?.remove(); 'done'`)
console.log('done')
process.exit(0)
