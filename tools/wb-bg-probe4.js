(() => {
  const el = document.getElementById('hermes-desktop-custom-css');
  const t = el ? el.textContent : '';
  return {
    bytes: t.length,
    head: t.slice(0, 90).replace(/\n/g, '\\n'),
    hasOldTop: t.includes('--composer-width'),
    hasFieldVars: t.includes('--wb-field-keep'),
    hasFieldLayer: t.includes('wb-field-drift'),
    hasShooter: t.includes('wb-shoot'),
    hasPauseRule: t.includes('data-renderer-animations-paused') && t.includes('animation-play-state: paused'),
    tail: t.slice(-160).replace(/\n/g, '\\n'),
    fieldRuleIndex: t.indexOf(':root:has([data-contrib-shell])'),
    ruleCount: (t.match(/\{/g) || []).length
  };
})()
