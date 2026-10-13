(() => {
  const html = document.documentElement;
  // find scrollable containers
  const scrollers = [];
  for (const el of document.querySelectorAll('div')) {
    if (el.scrollHeight > el.clientHeight + 40 && el.clientHeight > 300) {
      const cs = getComputedStyle(el);
      scrollers.push({
        sel: (el.getAttribute('data-slot') || '') + '|' + String(el.className).split(' ').slice(0, 3).join('.'),
        scrollH: el.scrollHeight, clientH: el.clientHeight,
        overflowY: cs.overflowY,
        willChange: cs.willChange,
        transform: cs.transform !== 'none',
        contain: cs.contain,
        overscroll: cs.overscrollBehavior,
        bg: cs.backgroundColor,
        rect: (() => { const r = el.getBoundingClientRect(); return [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)] })()
      });
    }
  }
  return {
    pausedAttr: html.hasAttribute('data-renderer-animations-paused'),
    hidden: document.hidden, focus: document.hasFocus(),
    scrollerCount: scrollers.length,
    scrollers: scrollers.slice(0, 6)
  };
})()
