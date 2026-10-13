(async () => {
  const html = document.documentElement
  const out = {}
  const rafPts = []
  await new Promise((done) => {
    let n = 0
    const tick = (now) => { rafPts.push(Math.round(now)); if (++n >= 8) return done(); requestAnimationFrame(tick) }
    requestAnimationFrame(tick)
    setTimeout(done, 2000)
  })
  out.rafTimestamps = rafPts
  out.rafDeltas = rafPts.slice(1).map((v, i) => v - rafPts[i])

  html.removeAttribute('data-renderer-animations-paused')
  await new Promise(r => setTimeout(r, 400))
  const tf = () => getComputedStyle(html, '::before').transform
  const o1 = getComputedStyle(html, '::before').opacity
  const t1 = tf()
  const a1 = html.getAnimations({ subtree: true }).find(x => x.animationName === 'wb-field-drift')
  const c1 = a1 ? Number(a1.currentTime) : null
  await new Promise(r => setTimeout(r, 1500))
  const t2 = tf()
  const a2 = html.getAnimations({ subtree: true }).find(x => x.animationName === 'wb-field-drift')
  const c2 = a2 ? Number(a2.currentTime) : null
  out.transform1 = t1
  out.transform2 = t2
  out.transformChanged = t1 !== t2
  out.currentTime1 = c1
  out.currentTime2 = c2
  out.ctChanged = c1 !== c2
  out.sameAnimObj = a1 === a2
  out.timelineCurrentTime = document.timeline.currentTime
  out.rateHint = null
  // restore
  html.setAttribute('data-renderer-animations-paused', '')
  return out
})()
