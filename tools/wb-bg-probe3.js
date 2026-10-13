(() => {
  const cssEl = document.getElementById('hermes-desktop-custom-css');
  const testEl = document.getElementById('wb-bg-test');
  const html = document.documentElement;
  const g = (el, pe) => {
    const cs = getComputedStyle(el, pe || null);
    return { anim: cs.animationName, state: cs.animationPlayState, tr: cs.transform, bgImg: (cs.backgroundImage || '').slice(0, 60) };
  };
  return {
    skinCssPresent: !!cssEl,
    skinCssBytes: cssEl ? cssEl.textContent.length : 0,
    skinHasField: cssEl ? cssEl.textContent.includes('wb-field-drift') : false,
    skinHasOldRules: cssEl ? cssEl.textContent.includes('--composer-width') : false,
    testStylePresent: !!testEl,
    fieldLayer: g(html, '::before'),
    farStars: g(html, '::after'),
    nearStars: g(document.body, '::before'),
    shooter: g(document.body, '::after'),
    bodyBg: getComputedStyle(document.body).backgroundImage.slice(0, 130),
    tokens: {
      chat: getComputedStyle(html).getPropertyValue('--ui-chat-surface-background').trim(),
      terminal: getComputedStyle(html).getPropertyValue('--ui-terminal-surface-background').trim()
    }
  };
})()
