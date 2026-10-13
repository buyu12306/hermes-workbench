// One-shot E2E: open an agent's drawer on the workflow page, click 更新清单 (refresh-models),
// then read the drawer status line. Run: node 75-refresh-click-verify.mjs [agent]
const port = Number(process.env.HERMES_DESKTOP_CDP_PORT || 9333)
const agent = (process.argv[2] || 'workbuddy').toLowerCase()
const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json()
const main = targets.find((t) => t.type === 'page' && (t.url || '').startsWith('file://'))
  || targets.find((t) => t.type === 'page' && t.title === 'Hermes')
if (!main) { console.error('no main target; targets:', targets.map(t => t.url).join(' | ')); process.exit(1) }
const ws = new WebSocket(main.webSocketDebuggerUrl)
let id = 0
const pending = new Map()
ws.addEventListener('message', (ev) => { const m = JSON.parse(ev.data); if (pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id) } })
await new Promise((r) => ws.addEventListener('open', r))
const send = (method, params, timeoutMs = 240000) => new Promise((res) => {
  const i = ++id
  pending.set(i, res)
  ws.send(JSON.stringify({ id: i, method, params }))
  setTimeout(() => { if (pending.has(i)) { pending.delete(i); res({ __timeout: method }) } }, timeoutMs)
})

const expr = `(async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const norm = s => (s || '').replace(/\\s+/g, '');
  const log = [];
  const vis = e => !!(e && e.offsetParent !== null && e.getBoundingClientRect().width > 0);

  const labels = ['工作流图', 'Workflow', 'Workflow Graph'];
  const MARK = ['软件智能体池', '看板任务池', '实时任务流', 'Software agents', 'Kanban task pool'];
  const onPage = () => MARK.some(m => [...document.querySelectorAll('span, div, h1, h2, h3')].some(e => norm(e.textContent) === m));
  log.push('onPageAtStart:' + onPage());
  if (!onPage()) {
    let hit = null;
    for (const lab of labels) {
      const hits = [...document.querySelectorAll('button, a, [role="button"], li, span, div')]
        .filter(e => norm(e.textContent) === lab && vis(e));
      if (hits.length) { hit = hits[hits.length - 1]; break; }
    }
    if (!hit) return JSON.stringify({ ok: false, step: 'nav-not-found', log,
      navCandidates: [...document.querySelectorAll('button, a, [role="button"]')].filter(vis).map(e => ((e.textContent || '').trim()).slice(0, 30)).slice(0, 50) });
    let cand = hit;
    for (let level = 0; level < 5 && cand; level++) {
      cand.click();
      for (let i = 0; i < 12; i++) { await sleep(500); if (onPage()) break; }
      log.push('clicked-level:' + level + ' onPage:' + onPage());
      if (onPage()) break;
      cand = cand.parentElement;
    }
  }
  if (!onPage()) return JSON.stringify({ ok: false, step: 'nav-failed', log });

  const cands = [...document.querySelectorAll('[aria-label]')].filter(e => {
    const a = (e.getAttribute('aria-label') || '').toLowerCase();
    if (!a.includes('${agent}')) return false;
    const r = e.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && (a.includes('详情') || a.includes('details'));
  });
  const gear = cands[0] || null;
  if (!gear) return JSON.stringify({ ok: false, step: 'gear-not-found', log,
    detailAria: [...document.querySelectorAll('[aria-label]')].filter(e => /详情|details/i.test(e.getAttribute('aria-label') || '') && e.getBoundingClientRect().width > 0).map(e => e.tagName + '::' + e.getAttribute('aria-label')) });
  try { gear.click(); } catch (e) {
    gear.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
  }
  log.push('clicked-gear:' + gear.tagName);

  let btn = null;
  for (let i = 0; i < 12; i++) {
    await sleep(500);
    btn = [...document.querySelectorAll('button')].find(b => ((b.getAttribute('title') || '')).includes('重新抓取最新内置模型清单'))
      || [...document.querySelectorAll('button')].find(b => norm(b.textContent) === '更新清单');
    if (btn && vis(btn)) break;
    btn = null;
  }
  if (!btn) return JSON.stringify({ ok: false, step: 'refresh-btn-not-found', log,
    drawerButtons: [...document.querySelectorAll('button')].filter(vis).map(b => ((b.textContent || '').trim() + ' | ' + (b.getAttribute('title') || ''))).slice(0, 50) });
  btn.click(); log.push('clicked-refresh');

  let msg = '';
  for (let i = 0; i < 90; i++) {
    await sleep(1000);
    const sts = [...document.querySelectorAll('[role="status"]')].filter(vis)
      .map(e => (e.textContent || '').trim())
      .filter(t => t && (t.includes('清单') || t.includes('更新') || t.includes('失败') || t.toLowerCase().includes('list') || t.toLowerCase().includes('refresh')));
    if (sts.length) { msg = sts[sts.length - 1]; break; }
  }
  return JSON.stringify({ ok: !!msg, msg, log });
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
