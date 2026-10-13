// Bake a mid-flight shooting-star frame (static override) for a visual check.
import { writeFileSync } from 'node:fs'
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
const evalv = async (expression) => (await send('Runtime.evaluate', { expression, returnByValue: true })).result?.result?.value
const shot = async (path) => {
  for (let i = 1; i <= 4; i++) {
    const r = await send('Page.captureScreenshot', { format: 'png' })
    const data = r.result?.data
    if (data && data.length > 200000) { writeFileSync(path, Buffer.from(data, 'base64')); return { path, bytes: data.length } }
    await new Promise((r2) => setTimeout(r2, 1200))
  }
  return { path, failed: true }
}
console.log('bake:', await evalv(`(() => {
  let el = document.getElementById('wb-shoot-test');
  if (!el) { el = document.createElement('style'); el.id = 'wb-shoot-test'; document.head.appendChild(el); }
  el.textContent = ":root:has([data-contrib-shell]) body::after{animation:none !important;opacity:0.92 !important;transform:translate3d(-24vw,10vh,0) rotate(20deg) !important;}";
  const cs = getComputedStyle(document.body, '::after');
  return { opacity: cs.opacity, transform: cs.transform };
})()`))
await new Promise((r) => setTimeout(r, 400))
console.log('shot:', JSON.stringify(await shot(process.argv[2] || 'C:/Users/<用户名>/Desktop/hermes-agent-main/.build/workbench/wb-motion-B.png')))
console.log('cleanup:', await evalv(`document.getElementById('wb-shoot-test')?.remove(); 'ok'`))
process.exit(0)
