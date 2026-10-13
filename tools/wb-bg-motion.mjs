// Motion test for the workbench dynamic field.
// 1) sample our layers' animation state  2) fast-forward + prove motion
// 3) freeze the shooting star mid-flight for a screenshot  4) restore state.
import { writeFileSync } from 'node:fs'
const port = Number(process.env.HERMES_DESKTOP_CDP_PORT || 9333)
const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json()
const main = targets.find((t) => t.type === 'page' && (t.url || '').startsWith('file://'))
const ws = new WebSocket(main.webSocketDebuggerUrl)
let id = 0
const pending = new Map()
const events = []
ws.addEventListener('message', (ev) => {
  const m = JSON.parse(ev.data)
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id) }
  else if (m.method) events.push(m)
})
await new Promise((r) => ws.addEventListener('open', r))
const send = (method, params, timeoutMs = 20000) => new Promise((res) => {
  const i = ++id
  pending.set(i, res)
  ws.send(JSON.stringify({ id: i, method, params }))
  setTimeout(() => { if (pending.has(i)) { pending.delete(i); res({ __timeout: method }) } }, timeoutMs)
})
const evalv = async (expression) => {
  const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
  return r.result?.result?.value
}
const shot = async (path) => {
  for (let i = 1; i <= 4; i++) {
    const r = await send('Page.captureScreenshot', { format: 'png' }, 30000)
    const data = r.result?.data
    if (data && data.length > 200000) {
      writeFileSync(path, Buffer.from(data, 'base64'))
      return { path, bytes: Buffer.from(data, 'base64').length, attempt: i }
    }
    await new Promise((r2) => setTimeout(r2, 1200))
  }
  return { path, bytes: 0, failed: true }
}

const SAMPLE = `(() => {
  const html = document.documentElement
  const g = (el, pe) => {
    const cs = getComputedStyle(el, pe || null)
    return { anim: cs.animationName, dur: cs.animationDuration, state: cs.animationPlayState, tr: cs.transform, op: cs.opacity }
  }
  return {
    pausedAttr: html.hasAttribute('data-renderer-animations-paused'),
    field: g(html, '::before'),
    farStars: g(html, '::after'),
    nearStars: g(document.body, '::before'),
    shooter: g(document.body, '::after'),
    animCount: document.getAnimations().length
  }
})()`

console.log('--- initial state ---')
console.log(JSON.stringify(await evalv(SAMPLE), null, 1))

// 2) fast-forward
await evalv(`document.documentElement.removeAttribute('data-renderer-animations-paused'); 'attr-off'`)
await send('Animation.enable')
console.log('rate:', JSON.stringify(await send('Animation.setPlaybackRate', { playbackRate: 20 })))
await new Promise((r) => setTimeout(r, 1200))
const t1 = await evalv(SAMPLE)
console.log('--- t1 (rate 20) ---')
console.log(JSON.stringify({ field: t1.field.tr, far: t1.farStars.tr, shooterOp: t1.shooter.op }, null, 1))
const shotA = await shot(process.argv[2] || 'C:/Users/<用户名>/Desktop/hermes-agent-main/.build/workbench/wb-motion-A.png')
await new Promise((r) => setTimeout(r, 2500))
const t2 = await evalv(SAMPLE)
console.log('--- t2 (rate 20) ---')
console.log(JSON.stringify({ field: t2.field.tr, far: t2.farStars.tr, shooterOp: t2.shooter.op }, null, 1))
console.log('moved:', t1.field.tr !== t2.field.tr)

// 3) freeze the shooter mid-flight for a reliable capture
await evalv(`(() => {
  let el = document.getElementById('wb-shoot-test');
  if (!el) { el = document.createElement('style'); el.id = 'wb-shoot-test'; document.head.appendChild(el); }
  el.textContent = ":root:has([data-contrib-shell]) body::after{animation-delay:-29.9s !important;animation-play-state:paused !important;}";
  return getComputedStyle(document.body, '::after').opacity
})()`)
await new Promise((r) => setTimeout(r, 600))
console.log('--- shooter frozen ---')
console.log(JSON.stringify(await evalv(`(() => { const cs = getComputedStyle(document.body, '::after'); return { opacity: cs.opacity, transform: cs.transform } })()`), null, 1))
const shotB = await shot(process.argv[3] || 'C:/Users/<用户名>/Desktop/hermes-agent-main/.build/workbench/wb-motion-B.png')

// 4) restore
await evalv(`document.getElementById('wb-shoot-test')?.remove(); document.documentElement.setAttribute('data-renderer-animations-paused', ''); 'restored'`)
console.log('--- restored ---')
console.log(JSON.stringify(await evalv(SAMPLE), null, 1))
console.log('shots:', JSON.stringify([shotA, shotB]))
process.exit(0)
