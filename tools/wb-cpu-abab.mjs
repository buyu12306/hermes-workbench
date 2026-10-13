// A/B/A/B: steps() vs smooth easing, alternating to cancel order effects.
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
const evalv = async (expression) => (await send('Runtime.evaluate', { expression, returnByValue: true })).result?.result?.value
const setTest = (css) => evalv(`(() => { let el = document.getElementById('wb-cpu-test'); if (!el) { el = document.createElement('style'); el.id = 'wb-cpu-test'; document.head.appendChild(el); } el.textContent = ${JSON.stringify(css)}; return 'ok' })()`)
const sample = (tag) => {
  const out = execSync('powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:/Users/<用户名>/Desktop/hermes-agent-main/.build/workbench/wb-cpu-sample.ps1', { encoding: 'utf8', timeout: 30000 })
  // keep only the renderer + total split for readability
  const m = out.match(/total=([\d.]+)%/)
  const r = out.match(/renderer=([\d.]+)/)
  const g = out.match(/gpu-process=([\d.]+)/)
  const mm = out.match(/main=([\d.]+)/)
  console.log(tag.padEnd(24), `total=${m?.[1]}%  renderer=${r?.[1]}  gpu=${g?.[1]}  main=${mm?.[1]}`)
}

const G = ':root:has([data-contrib-shell])'
await evalv(`document.documentElement.removeAttribute('data-renderer-animations-paused'); 'on'`)
await new Promise(r => setTimeout(r, 400))

for (let round = 1; round <= 2; round++) {
  await setTest('')
  await sample(`R${round} A) steps  `)
  await setTest(`${G}::before{animation-timing-function: ease-in-out !important} ${G}::after{animation-timing-function: ease-in-out !important}`)
  await sample(`R${round} B) smooth `)
}
await setTest('')
await evalv(`document.getElementById('wb-cpu-test')?.remove(); document.documentElement.setAttribute('data-renderer-animations-paused',''); 'done'`)
console.log('done')
process.exit(0)
