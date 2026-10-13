@echo off
rem Hermes Agent Gateway - Messaging Platform Integration
cd /d C:\Users\<用户名>\AppData\Local\hermes
set "HERMES_HOME=C:\Users\<用户名>\AppData\Local\hermes"
set "PYTHONIOENCODING=utf-8"
set "HERMES_GATEWAY_DETACHED=1"
set "HERMES_SUPERVISED_CHILD=1"
set "VIRTUAL_ENV=C:\Users\<用户名>\Desktop\hermes-agent-main\.venv"
set "PYTHONPATH=C:\Users\<用户名>\Desktop\hermes-agent-main;%PYTHONPATH%"
C:\Users\<用户名>\Desktop\hermes-agent-main\.venv\Scripts\python.exe -m hermes_cli.main gateway run
exit /b 0
