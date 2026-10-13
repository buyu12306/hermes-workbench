/**
 * Workbench Live Field (v2) — companion for the 动态背景「深海流光」 skin section.
 *
 * Measured on this machine (Intel UHD iGPU): while the field animates, the
 * Hermes GPU process burns ~50% + DWM ~25% of the GPU just sitting there; with
 * the field static it drops to ~19%/10%, with it gone ~8%. A 60fps full-window
 * animation is simply too much for this iGPU to keep alongside scrolling.
 *
 * So the field now holds still BY DEFAULT and only drifts during idle windows:
 * this plugin grants `:root[data-wb-idle]` after ~12s without any use
 * (pointer moves, clicks, keys, wheel, touch), and yanks it back the moment
 * the user interacts or the mouse leaves the window. The CSS pauses the
 * animations unless the idle grant is present; a disabled/broken plugin
 * degrades to a permanently static background (still pretty, zero cost).
 *
 * Plain ESM, loaded uncompiled. No contributions — pure side effect + cleanup.
 */

const IDLE_MS = 12000
const RETRIGGER_MS = 1000

let timer = null
let lastWake = 0

const root = () => document.documentElement

const setActive = (on) => {
  const r = root()
  if (on) {
    if (!r.hasAttribute('data-wb-idle')) r.setAttribute('data-wb-idle', '')
  } else if (r.hasAttribute('data-wb-idle')) {
    r.removeAttribute('data-wb-idle')
  }
}

const schedule = () => {
  if (timer !== null) clearTimeout(timer)
  timer = setTimeout(() => {
    timer = null
    setActive(true)
  }, IDLE_MS)
}

const wake = () => {
  setActive(false)
  const now = Date.now()
  if (now - lastWake > RETRIGGER_MS) {
    lastWake = now
    schedule()
  }
}

const hold = () => {
  setActive(false)
  if (timer !== null) {
    clearTimeout(timer)
    timer = null
  }
}

export default {
  id: 'workbench-field',
  name: 'Workbench Live Field',
  description: 'Drifts the 动态背景 only during idle windows; holds it still while you use the app.',
  defaultEnabled: true,
  register(ctx) {
    const opts = { capture: true, passive: true }
    const interactive = ['wheel', 'scroll', 'touchmove', 'keydown', 'pointerdown', 'pointermove']
    for (const type of interactive) document.addEventListener(type, wake, opts)
    document.addEventListener('mouseleave', hold)
    document.addEventListener('mouseenter', wake)
    schedule() // boot: drift only after a quiet 12s
    ctx.onDispose(() => {
      for (const type of interactive) document.removeEventListener(type, wake, opts)
      document.removeEventListener('mouseleave', hold)
      document.removeEventListener('mouseenter', wake)
      if (timer !== null) {
        clearTimeout(timer)
        timer = null
      }
      setActive(false)
    })
  }
}
