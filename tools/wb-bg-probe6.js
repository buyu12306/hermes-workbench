(() => {
  const html = document.documentElement;
  const frosted = [];
  const all = document.querySelectorAll('*');
  for (const el of all) {
    const cs = getComputedStyle(el);
    const bf = cs.backdropFilter || cs.webkitBackdropFilter;
    if (bf && bf !== 'none') frosted.push((el.getAttribute('data-slot') || el.className.toString().split(' ')[0] || el.tagName) + ' → ' + bf.slice(0, 40));
  }
  return {
    pausedAttr: html.hasAttribute('data-renderer-animations-paused'),
    frostedCount: frosted.length,
    frosted: frosted.slice(0, 10),
    fieldAnim: getComputedStyle(html, '::before').animationPlayState,
    tfNow: getComputedStyle(html, '::before').transform.slice(0, 60)
  };
})()
