(async () => {
  const html = document.documentElement
  const out = {
    visibility: document.visibilityState,
    hidden: document.hidden,
    hasFocus: document.hasFocus(),
    pausedAttrBefore: html.hasAttribute('data-renderer-animations-paused'),
    fullscreen: document.fullscreenElement ? true : false
  }
  // 1) simple rAF tick test with timeout
  out.rafTick = await new Promise((done) => {
    const t = setTimeout(() => done('NO-TICK-1500ms'), 1500)
    requestAnimationFrame(() => { clearTimeout(t); done('ticked') })
  })
  // 2) remove pause attr, see if it comes back within 1.2s
  html.removeAttribute('data-renderer-animations-paused')
  out.pausedAfterRemove = html.hasAttribute('data-renderer-animations-paused')
  await new Promise(r => setTimeout(r, 1200))
  out.pausedStillGone = !html.hasAttribute('data-renderer-animations-paused')
  // 3) does the field animation currentTime advance now?
  const a = html.getAnimations({ subtree: true }).find(x => x.animationName === 'wb-field-drift')
  const t0 = a ? Number(a.currentTime) : null
  await new Promise(r => setTimeout(r, 1200))
  const t1 = a ? Number(a.currentTime) : null
  out.fieldAdvanceMs = t0 === null ? 'no-anim' : Math.round(t1 - t0)
  out.fieldPlayState = a ? a.playState : null
  // restore
  html.setAttribute('data-renderer-animations-paused', '')
  return out
})()
