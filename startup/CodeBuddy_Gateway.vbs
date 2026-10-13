Set sh = CreateObject("WScript.Shell")
sh.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -File ""C:\Users\<用户名>\AppData\Local\hermes\codebuddy-gateway\supervisor.ps1""", 0, False
