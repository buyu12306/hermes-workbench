' Hermes Agent Gateway - Messaging Platform Integration
Option Explicit
Dim sh, env, existing_pp
Set sh = CreateObject("WScript.Shell")
Set env = sh.Environment("PROCESS")
env.Item("HERMES_HOME") = "C:\Users\<用户名>\AppData\Local\hermes"
env.Item("PYTHONIOENCODING") = "utf-8"
env.Item("HERMES_GATEWAY_DETACHED") = "1"
env.Item("HERMES_SUPERVISED_CHILD") = "1"
env.Item("VIRTUAL_ENV") = "C:\Users\<用户名>\Desktop\hermes-agent-main\.venv"
existing_pp = env.Item("PYTHONPATH")
If Len(existing_pp) > 0 Then
  env.Item("PYTHONPATH") = "C:\Users\<用户名>\Desktop\hermes-agent-main;" & existing_pp
Else
  env.Item("PYTHONPATH") = "C:\Users\<用户名>\Desktop\hermes-agent-main"
End If
sh.CurrentDirectory = "C:\Users\<用户名>\AppData\Local\hermes"
sh.Run "C:\Users\<用户名>\Desktop\hermes-agent-main\.venv\Scripts\python.exe -m hermes_cli.main gateway run", 0, False
