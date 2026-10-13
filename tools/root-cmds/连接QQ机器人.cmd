@echo off
chcp 65001 >nul
title 连接 QQ 机器人（Hermes）
cd /d C:\Users\<用户名>\Desktop\hermes-agent-main
set PYTHONIOENCODING=utf-8
echo ========================================
echo   Hermes x QQ 机器人 一键绑定
echo   手机上打开 QQ 扫描本窗口中的二维码
echo ========================================
echo.
".venv\Scripts\python.exe" .build\workbench\82-qq-onboard.py
echo.
echo === 写入配置 ===
".venv\Scripts\python.exe" .build\workbench\86-apply-qq-env.py
echo === 重启网关让 QQ 通道生效 ===
powershell -NoProfile -ExecutionPolicy Bypass -File .build\workbench\83-gateway-relaunch.ps1
echo 等待网关启动...
timeout /t 20 /nobreak >nul
".venv\Scripts\hermes.exe" gateway status
echo.
echo 完成！回到 Hermes 桌面端告诉我，我会继续验证。
pause
