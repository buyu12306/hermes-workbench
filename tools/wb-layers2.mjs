// Enumerate composited layers; check whether the field pseudos have their own
// layers with activeAnimation reasons (composited) or not (main-thread).
const port = Number(process.env.HERMES_DESKTOP_CDP_PORT || 9333)
const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json()
const main = targets.find((t) => t.type === 'page' && (t.url || '').startsWith('file://'))
const ws = new WebSocket(main.webSocketDebuggerUrl)
let id = 0
const pending = new Map()
let layers = null
ws.addEventListener('message', (ev) => {
  const m = JSON.parse(ev.data)
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id) }
  else if (m.method === 'LayerTree.layerTreeDidChange' && m.params?.layers) layers = m.params.layers
})
await new Promise((r) => ws.addEventListener('open', r))
const send = (method, params, timeoutMs = 20000) => new Promise((res) => {
  const i = ++id
  pending.set(i, res)
  ws.send(JSON.stringify({ id: i, method, params }))
  setTimeout(() => { if (pending.has(i)) { pending.delete(i); res({ __timeout: method }) } }, timeoutMs)
})
const evalv = async (expression) => (await send('Runtime.evaluate', { expression, returnByValue: true })).result?.result?.value

await evalv(`document.documentElement.removeAttribute('data-renderer-animations-paused'); 'on'`)
await new Promise((r) => setTimeout(r, 600))
await send('LayerTree.enable')
await new Promise((r) => setTimeout(r, 1500))
if (!layers) { console.log('no layers'); process.exit(1) }
const big = layers.filter((l) => l.width * l.height > 800000)
console.log('total layers:', layers.length, '| viewport-sized:', big.length)
for (const l of big) {
  const cr = await send('LayerTree.compositingReasons', { layerId: l.layerId })
  const reasons = cr.result?.compositingReasonIds || []
  console.log(
    'layer', String(l.layerId).padStart(5),
    (l.width + 'x' + l.height).padEnd(11),
    'name=' + JSON.stringify((l.name || '').slice(0, 46)).padEnd(48),
    'reasons=' + reasons.join(','),
    l.offscreen ? 'OFFSCREEN' : ''
  )
}
console.log('done')
process.exit(0)
