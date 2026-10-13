// List all CDP page targets and their quick DOM markers.
const port = Number(process.env.HERMES_DESKTOP_CDP_PORT || 9333)
const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json()
const pages = targets.filter((t) => t.type === 'page')
const results = []
for (const t of pages) {
  const ws = new WebSocket(t.webSocketDebuggerUrl)
  await new Promise((r) => ws.addEventListener('open', r))
  const evalOnce = (expression) => new Promise((res) => {
    const id = Math.floor(Math.random() * 1e9)
    const onMsg = (ev) => {
      const m = JSON.parse(ev.data)
      if (m.id === id) { ws.removeEventListener('message', onMsg); res(m) }
    }
    ws.addEventListener('message', onMsg)
    ws.send(JSON.stringify({ id, method: 'Runtime.evaluate', params: { expression, returnByValue: true } }))
    setTimeout(() => res({ timeout: true }), 8000)
  })
  const r = await evalOnce(`(() => ({
    url: location.href.slice(-80),
    title: document.title,
    hasContribShell: !!document.querySelector('[data-contrib-shell]'),
    hasHudShell: !!document.querySelector('[data-hud-shell]'),
    hasChatSurface: !!document.querySelector('[data-chat-surface]'),
    rootChildren: document.getElementById('root') ? document.getElementById('root').children.length : -1,
    bodyClass: (document.body.className || '').slice(0, 60)
  }))()`)
  ws.close()
  results.push({ target: t.url.slice(0, 90), value: r.result?.result?.value ?? r.error, timeout: r.timeout || false })
}
console.log(JSON.stringify(results, null, 1))
process.exit(0)
