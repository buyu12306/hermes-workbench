# Definitive launch test: kill the current instance, then ask EXPLORER (not this
# shell) to open the shortcut — exactly what a user double-click does, with
# Explorer's own environment block (the real test of the User-scope env var).
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

$lnk = Join-Path ([Environment]::GetFolderPath('Desktop')) ('Hermes ' + [char]0x5DE5 + [char]0x4F5C + [char]0x53F0 + '.lnk')
# Delegate to the running explorer.exe so the child inherits EXPLORER's env block.
& explorer.exe $lnk
Write-Output ("asked explorer to open: " + $lnk)
Start-Sleep -Seconds 12
Get-Process Hermes -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle } | Select-Object Id, MainWindowTitle | Format-Table -AutoSize
