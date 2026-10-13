(() => {
  const html = document.documentElement
  const cssEl = document.getElementById('hermes-desktop-custom-css')
  const css = cssEl ? cssEl.textContent : ''
  const g = (el, pe) => { const cs = getComputedStyle(el, pe); return { anim: cs.animationName, dur: cs.animationDuration, tf: cs.animationTimingFunction, state: cs.animationPlayState } }
  const ice = (v) => getComputedStyle(html).getPropertyValue(v).trim()
  return {
    accent: ice('--theme-primary'),
    chrome: ice('--ui-bg-chrome'),
    cssSteps: css.includes('steps(240') && css.includes('steps(208'),
    cssFrostRule: css.includes('backdrop-filter: none'),
    cssBodyBeforeRule: /body::before\s*\{/.test(css),
    fieldLayer: g(html, '::before'),
    nearLayer: g(html, '::after'),
    shooter: g(document.body, '::after'),
    pausedAttr: html.hasAttribute('data-renderer-animations-paused')
  }
})()
