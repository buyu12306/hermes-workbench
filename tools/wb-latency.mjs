// (a) live CPU snapshot; (b) single wheel-dispatch latency: cold-animating vs pre-paused vs static.
import { execSync } from 'node:child_process'
const port = Number(process.env.HERMES_DESKTOP_CDP_PORT || 9333)
const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json()
const main = targets.find((t) => t.type === 'page' && (t.url || '').startsWith('file://'))
const ws = new WebSocket(main.webSocketDebuggerUrl)
let id = 0
const pending = new Map()
ws.addEventListener('message', (ev) => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id) } })
await new Promise((r) => ws.addEventListener('open', r))
const send = (method, params, timeoutMs = 40000) => new Promise((res) => {
  const i = ++id
  pending.set(i, res)
  ws.send(JSON.stringify({ id: i, method, params }))
  setTimeout(() => { if (pending.has(i)) { pending.delete(i); res({ __timeout: method }) } }, timeoutMs)
})
const evalv = async (expression) => {
  const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
  if (r.result?.exceptionDetails) console.log('EXC:', (r.result.exceptionDetails.exception?.description || '').slice(0, 160))
  return r.result?.result?.value
}
const setTest = (css) => evalv(`(() => { let el = document.getElementById('wb-scroll-test'); if (!el) { el = document.createElement('style'); el.id='wb-scroll-test'; document.head.appendChild(el); } el.textContent = ${JSON.stringify(css)}; return 'ok' })()`)

console.log('--- (a) live CPU over 6s (top burners) ---')
const psOut = execSync('powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:/Users/<用户名>/Desktop/hermes-agent-main/.build/workbench/wb-cpu-sample.ps1', { encoding: 'utf8', timeout: 30000 })
console.log(psOut.trim())
const ps2 = `$procs = Get-Process | Sort-Object CPU -Descending | Select-Object -First 10
$t1 = @{}; foreach ($p in $procs) { $t1[$p.Id] = $p.CPU }
Start-Sleep -Seconds 5
$rows = @()
foreach ($p in ($procs | Where-Object { [System.Diagnostics.Process]::GetProcessById($_.Id) })) { }
foreach ($p in (Get-Process | Where-Object { $t1.ContainsKey($_.Id) })) {
  $d = [math]::Round(($p.CPU - $t1[$p.Id]) / 5 * 100, 1)
  if ($d -gt 0) { $rows += ($p.ProcessName + '=' + $d + '%') }
}
$rows -join '  '`
const { execSync: ex2 } = await import('node:child_process')
const { writeFileSync } = await import('node:fs')
writeFileSync('C:/Users/<用户名>/Desktop/hermes-agent-main/.build/workbench/wb-top.ps1', ps2)
console.log(ex2('powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:/Users/<用户名>/Desktop/hermes-agent-main/.build/workbench/wb-top.ps1', { encoding: 'utf8', timeout: 30000 }).trim())

console.log('--- (b) wheel dispatch latency (ms per single event) ---')
const G = ':root:has([data-contrib-shell]):not(:has([data-hud-shell]))'
await evalv(`document.documentElement.removeAttribute('data-renderer-animations-paused'); 'on'`)

const latencyRun = async (label, setup) => {
  await setup()
  const times = []
  for (let i = 0; i < 5; i++) {
    const t0 = Date.now()
    await send('Input.dispatchMouseEvent', { type: 'mouseWheel', x: 870, y: 400, deltaX: 0, deltaY: 160 })
    times.push(Date.now() - t0)
    await new Promise(r => setTimeout(r, 800))
  }
  console.log(`${label.padEnd(34)} per-dispatch ms: ${times.join(', ')}`)
}

await latencyRun('cold (field animating)', async () => { await setTest('') })
await latencyRun('pre-paused (data-wb-scroll set)', async () => { await setTest(''); await evalv(`document.documentElement.setAttribute('data-wb-scroll',''); 'x'`) })
await evalv(`document.documentElement.removeAttribute('data-wb-scroll'); 'x'`)
await latencyRun('static field (animation:none)', async () => { await setTest(`${G}::before,${G}::after,${G} body::after{animation:none !important}`) })

await setTest('')
await evalv(`document.getElementById('wb-scroll-test')?.remove(); document.documentElement.setAttribute('data-renderer-animations-paused',''); 'done'`)
console.log('done')
process.exit(0)
