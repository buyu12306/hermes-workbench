# 13b-swap.ps1 - stop the workbench, swap in the freshly packed build, relaunch with CDP.
# Pure ASCII only (PS 5.1 on this box parses .ps1 as GBK; non-ASCII breaks it).
$ErrorActionPreference = 'Continue'
$repo = 'C:\Users\<用户名>\Desktop\hermes-agent-main'
$exePath = "$repo\apps\desktop\release\win-unpacked\Hermes.exe"
$unpacked = "$repo\apps\desktop\release\win-unpacked"
$backupDir = "$repo\apps\desktop\release\win-unpacked.pre-perf1"
$log = "$repo\.build\workbench\13b-swap.log"
function L($m) { ((Get-Date -Format 'HH:mm:ss') + ' ' + $m) | Out-File -Append -Encoding utf8 $log }

L 'START swap (perf1 hidden-stream derate)'

# 1) kill the app + its backend serve (path/command-matched, scoped to this checkout)
$targets = Get-CimInstance Win32_Process | Where-Object {
    ($_.Name -eq 'Hermes.exe' -and $_.ExecutablePath -eq $exePath) -or
    ($_.Name -eq 'python.exe' -and $_.CommandLine -match 'hermes_cli\.main serve' -and $_.CommandLine -match 'hermes-agent-main')
}
foreach ($p in $targets) { L ("killing " + $p.ProcessId + " " + $p.Name); Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }
for ($i = 0; $i -lt 25; $i++) {
    $alive = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'Hermes.exe' -and $_.ExecutablePath -eq $exePath })
    if ($alive.Count -eq 0) { break }
    Start-Sleep -Seconds 1
}
Start-Sleep -Seconds 2
L 'app + backend stopped'

# 2) move the old unpacked dir aside (kept for rollback)
if (-not (Test-Path $unpacked)) {
    L 'WARN: unpacked dir missing; packing into a fresh dir'
} else {
    if (Test-Path $backupDir) { Remove-Item -Recurse -Force $backupDir -ErrorAction SilentlyContinue }
    Move-Item -Force $unpacked $backupDir
    L 'old unpacked moved to win-unpacked.pre-perf1'
}

# 3) clear stale electron-builder download locks, then pack (03-pack.sh carries env + mirrors)
Get-ChildItem $env:TEMP -Filter 'eb-dl-*' -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
$bash = "$env:LOCALAPPDATA\hermes\git\bin\bash.exe"
L 'packing (03-pack.sh)...'
& $bash "$repo/.build/workbench/03-pack.sh" *>> "$repo\.build\workbench\02-03-pack-perf1.out"
$packOk = Test-Path $exePath
L ("pack done; new exe present: " + $packOk)

# 4) on failure restore the previous build so the user always has a working app
if (-not $packOk) {
    L 'pack FAILED - restoring previous build'
    if (Test-Path $unpacked) { Remove-Item -Recurse -Force $unpacked -ErrorAction SilentlyContinue }
    if (Test-Path "$backupDir\Hermes.exe") { Move-Item -Force $backupDir $unpacked; L 'previous build restored' }
}

# 5) relaunch with the CDP debug port
$env:HERMES_DESKTOP_HERMES_ROOT = $repo
$env:HERMES_CUA_DRIVER_CMD = 'C:\Users\<用户名>\AppData\Local\hermes\cua-driver\cua-driver.exe'
L 'launching with --remote-debugging-port=9333'
Start-Process -FilePath $exePath -ArgumentList '--remote-debugging-port=9333'
Start-Sleep -Seconds 14
(Get-Process Hermes -ErrorAction SilentlyContinue | Select-Object Id, MainWindowTitle | Format-Table -AutoSize | Out-String).Trim() | Out-File -Append -Encoding utf8 $log
L 'DONE'
