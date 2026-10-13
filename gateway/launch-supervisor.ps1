# launch-supervisor.ps1 — relaunch the codebuddy-gateway supervisor via the Startup VBS (no kills).
Start-Process wscript.exe -ArgumentList '"C:\Users\<用户名>\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\CodeBuddy_Gateway.vbs"'
Write-Output 'supervisor launch requested'
