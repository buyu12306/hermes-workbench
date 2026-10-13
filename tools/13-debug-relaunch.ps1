# Kill the current (clean) instance, then relaunch WITH the CDP debug port for verification.
$ErrorActionPreference = 'Continue'
$exePath = 'C:\Users\<用户名>\Desktop\hermes-agent-main\apps\desktop\release\win-unpacked\Hermes.exe'

$targets = Get-CimInstance Win32_Process | Where-Object {
    ($_.Name -eq 'Hermes.exe' -and $_.ExecutablePath -eq $exePath) -or
    ($_.Name -eq 'python.exe' -and $_.CommandLine -match 'hermes_cli\.main serve' -and $_.CommandLine -match 'hermes-agent-main\\\.venv')
}
foreach ($p in $targets) {
    Write-Output ("killing " + $p.ProcessId + " " + $p.Name)
    Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 3

$env:HERMES_DESKTOP_HERMES_ROOT = 'C:\Users\<用户名>\Desktop\hermes-agent-main'
$env:HERMES_CUA_DRIVER_CMD = 'C:\Users\<用户名>\AppData\Local\hermes\cua-driver\cua-driver.exe'
Write-Output 'launching with --remote-debugging-port=9333'
Start-Process -FilePath $exePath -ArgumentList '--remote-debugging-port=9333'
Start-Sleep -Seconds 14
Get-Process Hermes -ErrorAction SilentlyContinue | Select-Object Id, MainWindowTitle | Format-Table -AutoSize
