# 83-gateway-relaunch.ps1 — kill the running gateway (by command line match) and relaunch via the service VBS.
# Never kill by process name (name matching could hit the desktop app or the agent itself).
$vbs = 'C:\Users\<用户名>\AppData\Local\hermes\gateway-service\Hermes_Gateway.vbs'
function Get-GatewayProcs { Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'hermes_cli\.main\s+gateway\s+run' } }
$gatewayProcs = Get-GatewayProcs
if (-not $gatewayProcs) {
  Write-Output 'no gateway process found'
} else {
  foreach ($p in $gatewayProcs) {
    Write-Output ("killing pid " + $p.ProcessId + " :: " + $p.CommandLine)
    taskkill /PID $p.ProcessId /F | Out-Null
  }
}
# wait until the old processes are really gone (max 15s) before relaunching
$cleared = $false
for ($i = 0; $i -lt 15; $i++) {
  Start-Sleep -Seconds 1
  if (-not (Get-GatewayProcs)) { $cleared = $true; break }
}
Write-Output ("old-processes-gone=" + $cleared)
Start-Process wscript.exe -ArgumentList $vbs
# verify the gateway process is back (max 40s)
$up = $false
for ($i = 0; $i -lt 20; $i++) {
  Start-Sleep -Seconds 2
  if (Get-GatewayProcs) { $up = $true; break }
}
if ($up) { Write-Output 'gateway process is back' } else { Write-Output 'WARN: gateway did not come back within 40s - check logs\gateway.log / gateway-exit-diag.log' }
