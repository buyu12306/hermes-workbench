@echo off
rem ============================================================
rem  Hermes workbench - keep-awake control
rem  Daemon:  .build\workbench\80-task-keepawake.py  (v3)
rem  status : current busy decision + daemon liveness + log tail (venv redirector shows 2 pids for 1 daemon -- normal)
rem  hold   : manual hold via %LOCALAPPDATA%\hermes\keep-awake.on
rem  release: remove the manual hold (back to auto)
rem  start  : launch the daemon (windowless, same as login autostart)
rem  stop   : kill daemon processes (pythonw + 80-task-keepawake only)
rem  Usage  : 90-keepawake.cmd [status^|hold^|release^|start^|stop^|cancel-shutdown]
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
if /i "%~1"=="cancel-shutdown" goto cancelsd
if "%~1"==""           goto status
echo Usage: 90-keepawake.cmd [status^|hold^|release^|start^|stop^|cancel-shutdown]
exit /b 1

:status
echo.
echo == decision now ==
"%PY%" "%SCRIPT%" --once
echo.
echo == daemon ==
powershell -NoProfile -Command "$p=Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python(w)?\.exe' -and $_.CommandLine -match '80-task-keepawake\.py' -and $_.CommandLine -notmatch '--once' }; if($p){ 'RUNNING  pids: ' + (($p | ForEach-Object ProcessId) -join ',') } else { '*** NOT RUNNING ***' }"
echo.
echo == log tail ==
powershell -NoProfile -Command "if (Test-Path '%LOG%') { Get-Content -LiteralPath '%LOG%' -Encoding UTF8 -Tail 6 } else { '(no log)' }"
exit /b 0

:hold
echo. > "%FLAG%"
echo Manual hold ON  ^(keep-awake.on created^)
powershell -NoProfile -Command "$p=Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python(w)?\.exe' -and $_.CommandLine -match '80-task-keepawake\.py' -and $_.CommandLine -notmatch '--once' }; if(-not $p){ & wscript.exe '%VBS%'; 'daemon was not running - started it' } else { 'daemon already running; HOLD engages within 30s' }"
exit /b 0

:release
if exist "%FLAG%" del "%FLAG%"
echo Manual hold OFF  ^(keep-awake.on removed^)
powershell -NoProfile -Command "$p=Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python(w)?\.exe' -and $_.CommandLine -match '80-task-keepawake\.py' -and $_.CommandLine -notmatch '--once' }; if(-not $p){ & '%PY%' '%SCRIPT%' --restore } else { 'daemon running - power hold auto-releases when idle' }"
exit /b 0

:start
wscript.exe "%VBS%"
echo Daemon start requested via 81-keepawake-autostart.vbs
powershell -NoProfile -Command "Start-Sleep -Milliseconds 2000"
powershell -NoProfile -Command "$p=Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python(w)?\.exe' -and $_.CommandLine -match '80-task-keepawake\.py' -and $_.CommandLine -notmatch '--once' }; if($p){ 'RUNNING  pids: ' + (($p | ForEach-Object ProcessId) -join ',') } else { '*** NOT RUNNING ***' }"
exit /b 0

:stop
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python(w)?\.exe' -and $_.CommandLine -match '80-task-keepawake\.py' -and $_.CommandLine -notmatch '--once' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }; 'stopped'"
powershell -NoProfile -Command "Start-Sleep -Milliseconds 800; try { $s = Get-Content -Raw '%LOCALAPPDATA%\hermes\keepawake-power.json' -Encoding UTF8 | ConvertFrom-Json } catch { $s = $null }; if ($s -and $s.applied) { & '%PY%' '%SCRIPT%' --restore } elseif ($s) { 'power state: not held' } else { 'no state file; if idle sleep misbehaves check: powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE' }"
exit /b 0

:cancelsd
chcp 65001 >nul
echo.
echo == 取消关机倒计时 ==
shutdown.exe -a
echo == 终止 88-watch-shutdown 守护（按命令行匹配）==
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python(w)?\.exe' -and $_.CommandLine -match '88-watch-shutdown\.py' } | ForEach-Object { 'killing pid ' + $_.ProcessId; Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; 'done'"
exit /b 0
