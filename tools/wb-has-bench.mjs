// Benchmark: cost of the field's :has() gates under DOM-mutation load.
// Configs: FULL (our CSS as shipped) | STRIPPED (our section removed) | ATTR (gates
// rewritten to :root[data-wb-bench], attribute pre-set) — previews the plugin-gated variant.
const port = Number(process.env.HERMES_DESKTOP_CDP_PORT || 9333)
const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json()
const main = targets.find((t) => t.type === 'page' && (t.url || '').startsWith('file://'))
const ws = new WebSocket(main.webSocketDebuggerUrl)
let id = 0
const pending = new Map()
ws.addEventListener('message', (ev) => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id) } })
await new Promise((r) => ws.addEventListener('open', r))
const send = (method, params, timeoutMs = 40000) => new Promise((res) => {
  const i = ++id
  pending.set(i, res)
  ws.send(JSON.stringify({ id: i, method, params }))
  setTimeout(() => { if (pending.has(i)) { pending.delete(i); res({ __timeout: method }) } }, timeoutMs)
})
const evalv = async (expression) => {
  const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
  if (r.result?.exceptionDetails) console.log('EVAL EXCEPTION:', (r.result.exceptionDetails.exception?.description || '').slice(0, 300))
  return r.result?.result?.value
}
await send('Performance.enable')

const SET_CSS = (css) => `(() => { const el = document.getElementById('hermes-desktop-custom-css'); if (!window.__wbSavedCss) window.__wbSavedCss = el.textContent; el.textContent = ${JSON.stringify(css)}; return el.textContent.length })()`

const RUN_BURST = `(async () => {
  // scratch subtree with realistic depth; mutations are the load
  let host = document.getElementById('wb-bench-host');
  if (!host || !window.__benchNodes || !window.__benchNodes.length) {
    host?.remove();
    host = document.createElement('div');
    host.id = 'wb-bench-host';
    host.style.cssText = 'position:fixed;left:-9999px;top:0;width:300px;height:600px';
    document.body.appendChild(host);
    const divs = [host];
    let chain = host;
    for (let i = 0; i < 40; i++) {
      const d = document.createElement('div');
      d.className = 'bench-row b' + (i % 7) + ' flex items-center gap-2 rounded-md';
      d.setAttribute('data-bench-depth', String(i));
      chain.appendChild(d);
      chain = d;
      divs.push(d);
    }
    window.__benchNodes = [];
    for (let i = 0; i < 60; i++) {
      const s = document.createElement('span');
      s.className = 'bench-text';
      s.textContent = 'x'.repeat(80);
      divs[1 + (i % 40)].appendChild(s);
      window.__benchNodes.push(s.firstChild);
    }
  }
  const nodes = window.__benchNodes;
  const t0 = performance.now();
  for (let i = 0; i < 8000; i++) {
    const n = nodes[i % nodes.length];
    n.nodeValue = String(i % 10) + n.nodeValue.slice(1);
  }
  return { burstMs: Math.round(performance.now() - t0), mutations: 8000, first: nodes[0].nodeValue.slice(0, 3) }
})()`

const metrics = async () => {
  const m = await send('Performance.getMetrics')
  const get = (n) => { const e = m.result?.metrics?.find(x => x.name === n); return e ? e.value : -1 }
  return { task: get('TaskDuration'), style: get('RecalcStyleDuration'), script: get('ScriptDuration') }
}

const runOnce = async (tag) => {
  // warm-up (JIT + first style)
  await evalv(RUN_BURST)
  const m0 = await metrics()
  const r1 = await evalv(RUN_BURST)
  const r2 = await evalv(RUN_BURST)
  const m1 = await metrics()
  console.log(`${tag} burst ${r1.burstMs}ms+${r2.burstMs}ms | task +${(m1.task - m0.task).toFixed(3)}s style +${(m1.style - m0.style).toFixed(3)}s script +${(m1.script - m0.script).toFixed(3)}s`)
}

// FULL: current tag content
await runOnce('FULL    (shipped :has) ')

// STRIPPED: remove our section (everything from our first selector on)
const strippedInfo = await evalv(`(() => {
  const el = document.getElementById('hermes-desktop-custom-css');
  window.__wbSavedCss = el.textContent;
  const i = el.textContent.indexOf(':root:has([data-contrib-shell])');
  const stripped = i > 0 ? el.textContent.slice(0, i) : el.textContent;
  el.textContent = stripped;
  return { strippedChars: stripped.length, removed: el.textContent.length !== window.__wbSavedCss.length };
})()`)
console.log('stripped:', JSON.stringify(strippedInfo))
await runOnce('STRIPPED (no field css) ')

// ATTR: full css but gates rewritten to a root attribute (plugin-gated preview)
const attrInfo = await evalv(`(() => {
  const el = document.getElementById('hermes-desktop-custom-css');
  const full = window.__wbSavedCss;
  const rewritten = full
    .replaceAll(':root:has([data-contrib-shell]):not(:has([data-hud-shell]))', ':root[data-wb-bench]')
    .replaceAll(':root[data-renderer-animations-paused]:has([data-contrib-shell]):not(:has([data-hud-shell]))', ':root[data-renderer-animations-paused][data-wb-bench]');
  el.textContent = rewritten;
  document.documentElement.setAttribute('data-wb-bench', '');
  return { hasHasLeft: rewritten.includes(':has([data-contrib-shell])'), len: rewritten.length };
})()`)
console.log('attr rewrite:', JSON.stringify(attrInfo))
await runOnce('ATTR    (plugin gate)    ')
const fieldStillOn = await evalv(`getComputedStyle(document.documentElement, '::before').animationName`)
console.log('field still animating under ATTR variant:', fieldStillOn)

// restore original css + cleanup scratch + attr
await evalv(`(() => {
  const el = document.getElementById('hermes-desktop-custom-css');
  el.textContent = window.__wbSavedCss;
  document.documentElement.removeAttribute('data-wb-bench');
  document.getElementById('wb-bench-host')?.remove();
  return 'restored';
})()`)
console.log('restored')
process.exit(0)
