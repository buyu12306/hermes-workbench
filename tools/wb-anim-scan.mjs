// wb-anim-scan.mjs — locate every RUNNING CSS animation in the live app window
const port = Number(process.env.HERMES_DESKTOP_CDP_PORT || 9333)
const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json()
const main = targets.find((t) => t.type === 'page' && (t.url || '').startsWith('file://'))
const ws = new WebSocket(main.webSocketDebuggerUrl)
let id = 0
const pending = new Map()
ws.addEventListener('message', (ev) => {
  const m = JSON.parse(ev.data)
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id) }
})
await new Promise((r) => ws.addEventListener('open', r))
const send = (method, params) => new Promise((res) => {
  const i = ++id
  pending.set(i, res)
  ws.send(JSON.stringify({ id: i, method, params }))
})
const expr = `(() => {
  const out = []
  const els = document.querySelectorAll('*')
  for (const el of els) {
    for (const p of ['', '::before', '::after']) {
      let cs
      try { cs = getComputedStyle(el, p || null) } catch (e) { continue }
      const nm = cs.animationName
      if (nm && nm !== 'none' && cs.animationPlayState === 'running') {
        const c = el.className
        const cn = (typeof c === 'string') ? c : ((c && c.baseVal) || '')
        const r = el.getBoundingClientRect()
        out.push({ n: nm, p: p || '', tag: el.tagName, cls: cn.slice(0, 90), id: el.id || '', w: Math.round(r.width), h: Math.round(r.height), top: Math.round(r.top) })
      }
    }
  }
  const rules = []
  for (const s of document.styleSheets) {
    let rs
    try { rs = s.cssRules } catch (e) { continue }
    for (const r of rs) {
      try { const t = r.cssText || ''; if (/shimmer|spinner-advance|arc-border/.test(t)) rules.push(t.slice(0, 260)) } catch (e) {}
    }
  }
  return JSON.stringify({ running: out, rules: rules.slice(0, 14), hash: location.hash })
})()`
const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true })
console.log(JSON.stringify(r.result && r.result.result ? r.result.result.value : r, null, 1))
process.exit(0)
