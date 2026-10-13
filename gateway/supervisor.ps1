# codebuddy-gateway supervisor — keep the local free-model gateway (port 8787) alive.
# v2: HTTP health probe (not just port presence), exponential backoff on crash loops,
#     child killed as a process tree on stop, logs rotated, stop-flag consumed on exit.
$dir  = "C:\Users\<用户名>\AppData\Local\hermes\codebuddy-gateway"
$uv   = "C:\Users\<用户名>\.local\bin\uv.exe"
$port = 8787
$slog = Join-Path $dir "supervisor.log"
$out  = Join-Path $dir "server.out"
$err  = Join-Path $dir "server.err"
$jlog = Join-Path $dir "proxy.jsonl"
$stopFlag = Join-Path $dir "gateway.stop"
function W([string]$m) { Add-Content -Path $slog -Value ("[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $m) -Encoding UTF8 }
function Rotate([string]$p) {
  try { if ((Test-Path $p) -and ((Get-Item $p).Length -gt 2MB)) { Move-Item -Force $p ($p + ".1") } } catch {}
}
function Healthy() {
  try {
    $r = Invoke-WebRequest -UseBasicParsing -Uri ("http://127.0.0.1:{0}/v1/models" -f $port) -Headers @{ Authorization = "Bearer codebuddy-local" } -TimeoutSec 5
    return ($r.StatusCode -eq 200)
  } catch { return $false }
}
function Stop-Child($p) {
  if ($p) { try { taskkill /PID $p.Id /T /F | Out-Null } catch {} }
}
W "supervisor start (pid $PID)"
$child = $null
$backoff = 10
while ($true) {
  if (Test-Path $stopFlag) {
    if ($child) { Stop-Child $child; W ("stop-flag: child pid " + $child.Id + " stopped (tree)") }
    Remove-Item -Force $stopFlag -ErrorAction SilentlyContinue
    W "stop-flag consumed; supervisor exit"
    break
  }
  if ($child) {
    try { $child.Refresh(); if ($child.HasExited) { W ("child exited; code=" + $child.ExitCode); $child = $null } } catch { $child = $null }
  }
  if (-not $child) {
    Rotate $out; Rotate $err; Rotate $jlog
    W "gateway not running; starting (backoff ${backoff}s)"
    $env:PYTHONIOENCODING = "utf-8"
    $child = Start-Process -FilePath $uv -ArgumentList @('run','--with','workbuddy2api','python','-u','-m','codebuddy_proxy','--host','127.0.0.1','--port',"$port",'--log-file',$jlog) -WorkingDirectory $dir -RedirectStandardOutput $out -RedirectStandardError $err -PassThru -WindowStyle Hidden
    W ("child pid " + $child.Id)
    # wait up to 90s for health, but honor the stop-flag while waiting
    $ok = $false
    for ($i = 0; $i -lt 18; $i++) {
      Start-Sleep -Seconds 5
      if (Test-Path $stopFlag) { break }
      if (Healthy) { $ok = $true; break }
    }
    if ($ok) { W "gateway healthy"; $backoff = 10 }
    elseif (Test-Path $stopFlag) { }   # next loop consumes the flag
    else {
      W "gateway did NOT become healthy (>=90s); restarting with backoff"
      Stop-Child $child; $child = $null
      Start-Sleep -Seconds $backoff
      $backoff = [Math]::Min(300, $backoff * 2)
    }
    continue
  }
  Start-Sleep -Seconds 30
  if (-not (Healthy)) {
    Start-Sleep -Seconds 5
    if (-not (Healthy)) {
      W "gateway unhealthy (HTTP probe x2 failed); restarting child"
      Stop-Child $child; $child = $null
      Start-Sleep -Seconds $backoff
      $backoff = [Math]::Min(300, $backoff * 2)
    }
  }
}
