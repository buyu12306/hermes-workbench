# Launch the packaged workbench for a verification run (detached), with a
# Chromium remote-debugging port for programmatic DOM checks if the app honors it.
$env:HERMES_DESKTOP_HERMES_ROOT = 'C:\Users\<用户名>\Desktop\hermes-agent-main'
$exe = 'C:\Users\<用户名>\Desktop\hermes-agent-main\apps\desktop\release\win-unpacked\Hermes.exe'
if (-not (Test-Path $exe)) { Write-Output "MISSING: $exe"; exit 1 }
Start-Process -FilePath $exe -ArgumentList '--remote-debugging-port=9333' -WorkingDirectory 'C:\Users\<用户名>\Desktop\hermes-agent-main'
Start-Sleep -Seconds 3
Get-Process Hermes -ErrorAction SilentlyContinue | Select-Object Id, ProcessName, MainWindowTitle | Format-Table -AutoSize
