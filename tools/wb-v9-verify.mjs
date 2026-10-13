// Final verify: layer structure + plugin keydown + bake the fixed shooting star for a look.
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
  if (r.result?.exceptionDetails) console.log('EXC:', (r.result.exceptionDetails.exception?.description || '').slice(0, 200))
  return r.result?.result?.value
}
const fs = await import('node:fs')
const shot = async (path) => {
  for (let i = 1; i <= 4; i++) {
    const r = await send('Page.captureScreenshot', { format: 'png' }, 30000)
    const d = r.result?.data
    if (d && d.length > 200000) { fs.writeFileSync(path, Buffer.from(d, 'base64')); return d.length }
    await new Promise((r2) => setTimeout(r2, 1200))
  }
  return 0
}

await evalv(`document.documentElement.removeAttribute('data-renderer-animations-paused'); 'on'`)

console.log('layers:', JSON.stringify(await evalv(`(() => {
  const g = (el, pe) => { const cs = getComputedStyle(el, pe); return cs.animationName + ' / ' + cs.animationPlayState }
  const css = document.getElementById('hermes-desktop-custom-css').textContent
  return {
    field: g(document.documentElement, '::before'),
    htmlAfter: g(document.documentElement, '::after'),
    shooter: g(document.body, '::after'),
    cssChars: css.length,
    hasTwinkle: css.includes('wb-twinkle'),
    hasRotateFix: css.includes('-12.5deg')
  }
})()`)))

// plugin keydown check
await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'PageDown', code: 'PageDown', windowsVirtualKeyCode: 34 })
await new Promise(r => setTimeout(r, 120))
console.log('keydown flag:', JSON.stringify(await evalv(`({ flag: document.documentElement.hasAttribute('data-wb-scroll'), play: getComputedStyle(document.documentElement, '::before').animationPlayState })`)))
await new Promise(r => setTimeout(r, 800))

// bake fixed shooter mid-flight + shoot
await evalv(`(() => { let el = document.getElementById('wb-shoot-fix-test'); if (!el) { el = document.createElement('style'); el.id = 'wb-shoot-fix-test'; document.head.appendChild(el); } el.textContent = ":root:has([data-contrib-shell]) body::after{animation:none !important;opacity:0.92 !important;transform:translate3d(-24vw,10vh,0) rotate(-12.5deg) !important}"; return 'baked' })()`)
await new Promise(r => setTimeout(r, 400))
console.log('shooter shot bytes:', await shot('C:/Users/<用户名>/Desktop/hermes-agent-main/.build/workbench/wb-shoot-fixed.png'))
await evalv(`document.getElementById('wb-shoot-fix-test')?.remove(); document.documentElement.setAttribute('data-renderer-animations-paused',''); 'clean'`)
console.log('clean shot bytes:', await shot('C:/Users/<用户名>/Desktop/hermes-agent-main/.build/workbench/wb-bg-v9.png'))
process.exit(0)
