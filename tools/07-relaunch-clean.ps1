# Kill ONLY the verification instance (win-unpacked Hermes.exe + its serve children),
# then relaunch through the new shortcut exactly as the user will.
$ErrorActionPreference = 'Continue'
$exePath = 'C:\Users\<用户名>\Desktop\hermes-agent-main\apps\desktop\release\win-unpacked\Hermes.exe'

$targets = Get-CimInstance Win32_Process | Where-Object {
    ($_.Name -eq 'Hermes.exe' -and $_.ExecutablePath -eq $exePath) -or
    ($_.Name -eq 'python.exe' -and $_.CommandLine -match 'hermes_cli\.main serve' -and $_.CommandLine -match 'hermes-agent-main\\\.venv')
}
foreach ($p in $targets) {
    Write-Output ("killing " + $p.ProcessId + " " + $p.Name + " :: " + ($p.CommandLine -replace '\s+',' ').Substring(0, [Math]::Min(110, ($p.CommandLine -replace '\s+',' ').Length)))
    Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 3

# Simulate the user's launch environment (Explorer already sees the User-scope var).
$env:HERMES_DESKTOP_HERMES_ROOT = 'C:\Users\<用户名>\Desktop\hermes-agent-main'
$lnk = Join-Path ([Environment]::GetFolderPath('Desktop')) ('Hermes ' + [char]0x5DE5 + [char]0x4F5C + [char]0x53F0 + '.lnk')
Write-Output ("launching: " + $lnk)
Start-Process $lnk
Start-Sleep -Seconds 10
Get-Process Hermes -ErrorAction SilentlyContinue | Select-Object Id, MainWindowTitle | Format-Table -AutoSize
