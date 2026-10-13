(() => {
  const html = document.documentElement;
  const cssEl = document.getElementById('hermes-desktop-custom-css');
  const css = cssEl ? cssEl.textContent : '';
  const g = (el, pe) => { const cs = getComputedStyle(el, pe); return cs.animationName + ' / ' + cs.animationDuration + ' / ' + cs.animationTimingFunction };
  const leftovers = ['wb-bg-test', 'wb-shoot-test', 'wb-perf-test', 'wb-perf-test2', 'wb-cpu-test', 'wb-bench-host']
    .filter((id) => document.getElementById(id));
  return {
    skinCss: css.length,
    field: g(html, '::before'),
    near: g(html, '::after'),
    shooter: g(document.body, '::after'),
    noSteps: !css.includes('steps(') || css.indexOf('steps(') === css.lastIndexOf('steps('),
    frostRule: css.includes('backdrop-filter: none'),
    leftovers,
    pausedAttr: html.hasAttribute('data-renderer-animations-paused'),
    frostedNow: (() => { let n = 0; for (const el of document.querySelectorAll('*')) { const bf = getComputedStyle(el).backdropFilter; if (bf && bf !== 'none') n++ } return n })()
  };
})()
