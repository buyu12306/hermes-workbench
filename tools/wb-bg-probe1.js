(() => {
  const pick = (el) => {
    if (!el) return null;
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    return {
      sel: describe(el),
      bg: cs.backgroundColor,
      bgImage: cs.backgroundImage === 'none' ? 'none' : cs.backgroundImage.slice(0, 160),
      rect: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)],
      pos: cs.position, z: cs.zIndex, op: cs.opacity
    };
  };
  const describe = (el) => {
    if (!el || el === document.documentElement) return 'html';
    if (el === document.body) return 'body';
    let s = el.tagName.toLowerCase();
    const slot = el.getAttribute && el.getAttribute('data-slot');
    if (slot) s += `[slot=${slot}]`;
    const cls = el.className && typeof el.className === 'string' ? el.className.split(' ').filter(Boolean).slice(0, 2).join('.') : '';
    if (cls) s += '.' + cls;
    return s;
  };
  const html = document.documentElement;
  const keys = {};
  for (let i = 0; i < localStorage.length; i++) {
    const k = localStorage.key(i);
    if (/hermes|skin|theme|translucen|glass/i.test(k)) keys[k] = (localStorage.getItem(k) || '').slice(0, 200);
  }
  const probeAt = (x, y) => {
    const el = document.elementFromPoint(x, y);
    const chain = [];
    let cur = el;
    while (cur && chain.length < 16) { chain.push(pick(cur)); cur = cur.parentElement; }
    return { hit: describe(el), chain };
  };
  const skineEls = [...document.querySelectorAll('style')].map((s) => ({
    len: s.textContent.length,
    head: s.textContent.slice(0, 80).replace(/\n/g, ' ')
  })).filter((s) => s.len > 0);
  return {
    url: location.href,
    attrs: {
      glass: html.getAttribute('data-hermes-glass'),
      glassOn: html.getAttribute('data-hermes-glass-on'),
      glassScope: html.getAttribute('data-hermes-glass-scope'),
      clear: html.getAttribute('data-hermes-clear'),
      paused: html.hasAttribute('data-renderer-animations-paused'),
      dir: html.getAttribute('dir'),
      theme: html.getAttribute('data-theme') || html.getAttribute('data-appearance') || null
    },
    htmlInline: (html.getAttribute('style') || '').slice(0, 300),
    ls: keys,
    htmlBg: getComputedStyle(html).backgroundColor,
    body: pick(document.body),
    root: pick(document.getElementById('root')),
    contribShell: pick(document.querySelector('[data-contrib-shell]')),
    sidebarWrapper: pick(document.querySelector("[data-slot='sidebar-wrapper']")),
    center: probeAt(Math.round(innerWidth * 0.5), Math.round(innerHeight * 0.5)),
    sidebar: probeAt(60, Math.round(innerHeight * 0.5)),
    rightSide: probeAt(innerWidth - 80, Math.round(innerHeight * 0.4)),
    styles: skineEls
  };
})()
