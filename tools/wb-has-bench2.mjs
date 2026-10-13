// Benchmark v2: force style recalcs synchronously so costs are measurable while occluded.
// Configs: FULL (shipped) | STRIPPED (our section removed = original customCSS only)
//          | ATTR (gates rewritten to a plain root attribute = plugin-gate preview)
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
const evalv = async (expression) => {
  const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
  if (r.result?.exceptionDetails) console.log('EVAL EXCEPTION:', (r.result.exceptionDetails.exception?.description || '').slice(0, 220))
  return r.result?.result?.value
}

const BURST = `(async () => {
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
  let flushMs = 0;
  const t0 = performance.now();
  for (let i = 0; i < 8000; i++) {
    nodes[i % nodes.length].nodeValue = String(i % 10) + nodes[i % nodes.length].nodeValue.slice(1);
    if (i % 500 === 499) {
      const f0 = performance.now();
      host.getBoundingClientRect();          // forces style recalc (+layout) of whatever is dirty
      flushMs += performance.now() - f0;
    }
  }
  const totalMs = performance.now() - t0;
  return { totalMs: Math.round(totalMs), flushMs: Math.round(flushMs), mutMs: Math.round(totalMs - flushMs) };
})()`

const runBurst = async () => {
  const a = await evalv(BURST)
  const b = await evalv(BURST)
  const c = await evalv(BURST)
  return `chunks: ${a.totalMs}/${b.totalMs}/${c.totalMs} ms  (flush ${a.flushMs}/${b.flushMs}/${c.flushMs})`
}

console.log('warmup:', await runBurst())

// FULL
console.log('FULL    (shipped :has) :', await runBurst())

// STRIPPED
await evalv(`(() => {
  const el = document.getElementById('hermes-desktop-custom-css');
  window.__wbSavedCss = window.__wbSavedCss || el.textContent;
  const i = el.textContent.indexOf(':root:has([data-contrib-shell])');
  el.textContent = i > 0 ? el.textContent.slice(0, i) : el.textContent;
  return 'stripped';
})()`)
console.log('STRIPPED (orig only)   :', await runBurst())

// ATTR
await evalv(`(() => {
  const el = document.getElementById('hermes-desktop-custom-css');
  el.textContent = window.__wbSavedCss
    .replaceAll(':root:has([data-contrib-shell]):not(:has([data-hud-shell]))', ':root[data-wb-bench]')
    .replaceAll(':root[data-renderer-animations-paused]:has([data-contrib-shell]):not(:has([data-hud-shell]))', ':root[data-renderer-animations-paused][data-wb-bench]');
  document.documentElement.setAttribute('data-wb-bench', '');
  return 'attr';
})()`)
console.log('ATTR    (plugin gate)  :', await runBurst())

// restore
await evalv(`(() => {
  const el = document.getElementById('hermes-desktop-custom-css');
  el.textContent = window.__wbSavedCss;
  document.documentElement.removeAttribute('data-wb-bench');
  document.getElementById('wb-bench-host')?.remove();
  return 'restored';
})()`)
console.log('restored')
process.exit(0)
