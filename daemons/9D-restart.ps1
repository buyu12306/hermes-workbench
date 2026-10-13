# 9D-restart.ps1 — restart keep-awake daemon with v3, kill duplicates, verify everything.
$repo = 'C:\Users\<用户名>\Desktop\hermes-agent-main'
$out = 'C:\Users\<用户名>\AppData\Local\hermes\cache\scratch\keepawake-deploy.txt'
$lines = @()

# 1) kill ALL matching pythonw instances (v2 duplicates included)
$p = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'pythonw.exe' -and $_.CommandLine -match '80-task-keepawake' })
$lines += 'killing: ' + (($p | ForEach-Object { $_.ProcessId }) -join ',')
$p | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 1
$r = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'pythonw.exe' -and $_.CommandLine -match '80-task-keepawake' })
$lines += 'remaining after kill: ' + $r.Count

# 2) start v3
Start-Process -FilePath "$repo\.venv\Scripts\pythonw.exe" -ArgumentList "$repo\.build\workbench\80-task-keepawake.py" -WindowStyle Hidden
Start-Sleep -Seconds 35

# 3) verify
$r = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'pythonw.exe' -and $_.CommandLine -match '80-task-keepawake' })
$lines += 'running now: ' + (($r | ForEach-Object { $_.ProcessId }) -join ',')
$lines += '=== --once ==='
$lines += (& "$repo\.venv\Scripts\python.exe" "$repo\.build\workbench\80-task-keepawake.py" --once 2>&1 | Out-String)
$lines += '=== keepawake.log tail 16 ==='
$lines += (Get-Content "$env:LOCALAPPDATA\hermes\logs\keepawake.log" -Tail 16 | Out-String)
$lines += '=== keepawake-power.json ==='
try { $lines += (Get-Content -Raw "$env:LOCALAPPDATA\hermes\keepawake-power.json") } catch { $lines += 'missing' }
$lines += '=== powercfg STANDBYIDLE 0x-lines ==='
$q = (powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE | Out-String)
$lines += (@($q -split "`n" | Where-Object { $_ -match '0x' }) -join "`n")

$lines | Out-File $out -Encoding utf8
'deploy done'
