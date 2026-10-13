@echo off
rem ============================================================
rem  Hermes workbench - keep-awake control
rem  Daemon:  .build\workbench\80-task-keepawake.py  (v2)
rem  status : current busy decision + daemon liveness + log tail
rem  hold   : manual hold via %LOCALAPPDATA%\hermes\keep-awake.on
rem  release: remove the manual hold (back to auto)
rem  start  : launch the daemon (windowless, same as login autostart)
rem  stop   : kill daemon processes (pythonw + 80-task-keepawake only)
rem  Usage  : 90-keepawake.cmd [status^|hold^|release^|start^|stop]
rem ============================================================
setlocal
set "PY=C:\Users\<用户名>\Desktop\hermes-agent-main\.venv\Scripts\python.exe"
set "SCRIPT=C:\Users\<用户名>\Desktop\hermes-agent-main\.build\workbench\80-task-keepawake.py"
set "VBS=C:\Users\<用户名>\Desktop\hermes-agent-main\.build\workbench\81-keepawake-autostart.vbs"
set "FLAG=%LOCALAPPDATA%\hermes\keep-awake.on"
set "LOG=%LOCALAPPDATA%\hermes\logs\keepawake.log"

if /i "%~1"=="hold"    goto hold
if /i "%~1"=="release" goto release
if /i "%~1"=="start"   goto start
if /i "%~1"=="stop"    goto stop
if /i "%~1"=="status"  goto status
if "%~1"==""           goto status
echo Usage: 90-keepawake.cmd [status^|hold^|release^|start^|stop]
exit /b 1

:status
echo.
echo == decision now ==
"%PY%" "%SCRIPT%" --once
echo.
echo == daemon ==
powershell -NoProfile -Command "$p=Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'pythonw.exe' -and $_.CommandLine -match '80-task-keepawake' }; if($p){ 'RUNNING  pids: ' + (($p | ForEach-Object ProcessId) -join ',') } else { '*** NOT RUNNING ***' }"
echo.
echo == log tail ==
powershell -NoProfile -Command "if (Test-Path '%LOG%') { Get-Content -LiteralPath '%LOG%' -Encoding UTF8 -Tail 6 } else { '(no log)' }"
exit /b 0

:hold
echo. > "%FLAG%"
echo Manual hold ON  ^(keep-awake.on created^)
powershell -NoProfile -Command "$p=Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'pythonw.exe' -and $_.CommandLine -match '80-task-keepawake' }; if(-not $p){ & wscript.exe '%VBS%'; 'daemon was not running - started it' } else { 'daemon already running; HOLD engages within 30s' }"
exit /b 0

:release
if exist "%FLAG%" del "%FLAG%"
echo Manual hold OFF  ^(keep-awake.on removed; auto resumes within 30s^)
exit /b 0

:start
wscript.exe "%VBS%"
echo Daemon start requested via 81-keepawake-autostart.vbs
timeout /t 2 >nul
powershell -NoProfile -Command "$p=Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'pythonw.exe' -and $_.CommandLine -match '80-task-keepawake' }; if($p){ 'RUNNING  pids: ' + (($p | ForEach-Object ProcessId) -join ',') } else { '*** NOT RUNNING ***' }"
exit /b 0

:stop
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'pythonw.exe' -and $_.CommandLine -match '80-task-keepawake' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }; 'stopped'"
exit /b 0
