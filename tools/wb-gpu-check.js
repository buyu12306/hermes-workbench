(() => {
  const c = document.createElement('canvas');
  const gl = c.getContext('webgl2') || c.getContext('webgl');
  let renderer = 'no-webgl', vendor = 'no-webgl';
  if (gl) {
    const dbg = gl.getExtension('WEBGL_debug_renderer_info');
    renderer = dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER);
    vendor = dbg ? gl.getParameter(dbg.UNMASKED_VENDOR_WEBGL) : gl.getParameter(gl.VENDOR);
  }
  return {
    webglRenderer: renderer,
    webglVendor: vendor,
    hardwareConcurrency: navigator.hardwareConcurrency,
    deviceMemory: navigator.deviceMemory || null,
    dpr: window.devicePixelRatio,
    screen: [screen.width, screen.height],
    // rough indicator of whether the compositor is likely on the GPU
    canvas2d: (() => { try { return !!document.createElement('canvas').getContext('2d'); } catch { return false } })()
  };
})()
