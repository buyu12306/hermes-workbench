(() => {
  const html = document.documentElement;
  return {
    visibility: document.visibilityState,
    hidden: document.hidden,
    hasFocus: document.hasFocus(),
    pausedAttr: html.hasAttribute('data-renderer-animations-paused'),
    timing: {
      now: performance.now(),
      raf: typeof requestAnimationFrame
    },
    animCount: document.getAnimations().length,
    anims: document.getAnimations().slice(0, 12).map(a => ({
      name: a.animationName || (a.effect && a.effect.getKeyframes && 'web'),
      target: (a.effect && a.effect.target) ? (a.effect.target.tagName + '.' + (String(a.effect.target.className).split(' ')[0] || '')) : null,
      state: a.playState, ct: a.currentTime
    })),
    // does anything currently use CSS animation that we could watch as a canary?
    canary: (() => {
      const el = document.querySelector('.shimmer, .kanban-arc, .progress-slide');
      if (!el) return null;
      const cs = getComputedStyle(el);
      return { sel: el.className, anim: cs.animationName, play: cs.animationPlayState, dur: cs.animationDuration };
    })()
  };
})()
