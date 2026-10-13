// Diagnose the workflow page: dump visible buttons (aria/title/text/geometry) to pick the right selectors.
const port = Number(process.env.HERMES_DESKTOP_CDP_PORT || 9333)
const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json()
const main = targets.find((t) => t.type === 'page' && (t.url || '').startsWith('file://'))
  || targets.find((t) => t.type === 'page' && t.title === 'Hermes')
if (!main) { console.error('no main target'); process.exit(1) }
const ws = new WebSocket(main.webSocketDebuggerUrl)
let id = 0
const pending = new Map()
ws.addEventListener('message', (ev) => { const m = JSON.parse(ev.data); if (pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id) } })
await new Promise((r) => ws.addEventListener('open', r))
const send = (method, params, timeoutMs = 60000) => new Promise((res) => {
  const i = ++id
  pending.set(i, res)
  ws.send(JSON.stringify({ id: i, method, params }))
  setTimeout(() => { if (pending.has(i)) { pending.delete(i); res({ __timeout: method }) } }, timeoutMs)
})

const expr = `(async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const norm = s => (s || '').replace(/\\s+/g, '');
  const MARK = ['软件智能体池', '看板任务池', '实时任务流'];
  const onPage = () => MARK.some(m => [...document.querySelectorAll('span, div, h1, h2, h3')].some(e => norm(e.textContent) === m));
  if (!onPage()) {
    const hits = [...document.querySelectorAll('button, a, [role="button"], li, span, div')]
      .filter(e => norm(e.textContent) === '工作流图');
    if (hits.length) hits[hits.length - 1].click();
    for (let i = 0; i < 16; i++) { await sleep(500); if (onPage()) break; }
  }
  await sleep(1500);
  const rows = [...document.querySelectorAll('button')].map(b => {
    const r = b.getBoundingClientRect();
    return { aria: (b.getAttribute('aria-label') || '').slice(0, 70), title: (b.getAttribute('title') || '').slice(0, 40),
      txt: (b.textContent || '').trim().slice(0, 26), w: Math.round(r.width), h: Math.round(r.height), off: b.offsetParent ? 1 : 0 };
  }).filter(x => /详情|details|workbuddy|看板|board|＋|加入|移出|打开|open/i.test(x.aria + ' ' + x.txt)).slice(0, 40);
  const det = [...document.querySelectorAll('[aria-label]')].filter(e => /详情|details/i.test(e.getAttribute('aria-label') || '')).map(e => {
    const r = e.getBoundingClientRect();
    return { tag: e.tagName, aria: e.getAttribute('aria-label').slice(0, 60), w: Math.round(r.width), h: Math.round(r.height), off: e.offsetParent ? 1 : 0 };
  });
  const detail = [...document.querySelectorAll('button[aria-label]')].filter(b => /详情|details/i.test(b.getAttribute('aria-label') || '')).length;
  const wbTexts = [...document.querySelectorAll('span, div, text, tspan')].filter(e => e.children.length === 0 && /workbuddy/i.test(e.textContent || '')).slice(0, 10).map(e => e.tagName + '|' + (e.textContent || '').trim().slice(0, 36));
  const svgCards = document.querySelectorAll('foreignObject').length;
  return JSON.stringify({ onPage: onPage(), n: rows.length, detailButtons: detail, svgCards, wbTexts, det, rows }, null, 1);
})()`

const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true })
if (r.__timeout) { console.error('EVAL TIMEOUT'); process.exit(2) }
if (r.result && r.result.exceptionDetails) {
  console.error('EXCEPTION:', (r.result.exceptionDetails.exception && r.result.exceptionDetails.exception.description) || JSON.stringify(r.result.exceptionDetails).slice(0, 400))
} else {
  const v = r.result && r.result.result ? r.result.result.value : r
  console.log(typeof v === 'string' ? v : JSON.stringify(v, null, 1))
}
process.exit(0)
