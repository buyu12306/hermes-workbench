// Verify: main window has no [data-hud-shell]; list composited layers.
const port = Number(process.env.HERMES_DESKTOP_CDP_PORT || 9333)
const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json()
const main = targets.find((t) => t.type === 'page' && (t.url || '').startsWith('file://'))
const ws = new WebSocket(main.webSocketDebuggerUrl)
let id = 0
const pending = new Map()
const layers = []
let lastTree = null
ws.addEventListener('message', (ev) => {
  const m = JSON.parse(ev.data)
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id) }
  else if (m.method === 'LayerTree.layerTreeDidChange' || m.method === 'LayerTree.layerPainted') {
    if (m.params?.layers) lastTree = m.params.layers
  }
})
await new Promise((r) => ws.addEventListener('open', r))
const send = (method, params, timeoutMs = 15000) => new Promise((res) => {
  const i = ++id
  pending.set(i, res)
  ws.send(JSON.stringify({ id: i, method, params }))
  setTimeout(() => { if (pending.has(i)) { pending.delete(i); res({ __timeout: method }) } }, timeoutMs)
})
const evalv = async (expression) => (await send('Runtime.evaluate', { expression, returnByValue: true })).result?.result?.value

console.log('main window has [data-hud-shell]?', await evalv(`!!document.querySelector('[data-hud-shell]')`))
console.log('pause attr:', await evalv(`document.documentElement.hasAttribute('data-renderer-animations-paused')`))
console.log('layer states:', JSON.stringify(await evalv(`(() => {
  const g = (el, pe) => { const cs = getComputedStyle(el, pe); return cs.animationPlayState + '/' + cs.animationName.split(',')[0] }
  return { field: g(document.documentElement, '::before'), far: g(document.documentElement, '::after'), near: g(document.body, '::before'), shooter: g(document.body, '::after') };
})()`)))

await send('LayerTree.enable')
await new Promise((r) => setTimeout(r, 1800))
if (lastTree) {
  console.log('layer count:', lastTree.length)
  for (const l of lastTree.slice(-14)) {
    console.log(' layer', l.layerId, l.backendNodeId, JSON.stringify(l.width + 'x' + l.height), 'offscreen=' + !!l.offscreen, (l.name || '').slice(0, 40))
  }
} else {
  console.log('no layerTree event captured')
}
process.exit(0)
