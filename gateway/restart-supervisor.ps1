# restart-supervisor.ps1 — one-off: stop the old codebuddy-gateway supervisor + child tree,
# relaunch via the Startup VBS, then leave the new supervisor running.
function Get-Sup { Get-CimInstance Win32_Process | Where-Object { ($_.ProcessId -ne $me) -and ($_.Name -eq 'powershell.exe') -and ($_.CommandLine -match 'codebuddy-gateway\\supervisor\.ps1') } }
function Get-Kids { Get-CimInstance Win32_Process | Where-Object { ($_.Name -match '^(uv|pythonw?)\.exe$') -and ($_.CommandLine -match 'workbuddy2api|codebuddy_proxy') } }
$me = $PID
$procs = @(Get-Sup) + @(Get-Kids)
$procs | ForEach-Object { Write-Output ('killing ' + $_.ProcessId + ' ' + $_.Name) }
$procs | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
$freed = $false
for ($i = 0; $i -lt 20; $i++) {
  Start-Sleep -Seconds 1
  if (-not (Get-NetTCPConnection -LocalPort 8787 -State Listen -ErrorAction SilentlyContinue)) { $freed = $true; break }
}
Write-Output ("port-free=" + $freed)
$stragglers = @(Get-Sup) + @(Get-Kids)
$stragglers | ForEach-Object { Write-Output ('killing-straggler ' + $_.ProcessId + ' ' + $_.Name); Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
if ($stragglers.Count -gt 0) { Start-Sleep -Seconds 3 }
for ($i = 0; $i -lt 15; $i++) {
  if (-not (Get-NetTCPConnection -LocalPort 8787 -State Listen -ErrorAction SilentlyContinue)) { break }
  Start-Sleep -Seconds 1
}
Start-Process wscript.exe -ArgumentList '"C:\Users\<用户名>\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\CodeBuddy_Gateway.vbs"'
Write-Output 'single supervisor launched'
