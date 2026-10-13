# 98-launch-powerprobe.ps1 — launch 97 elevated and wait for it.
Start-Process powershell.exe -Verb RunAs -Wait -ArgumentList @(
  '-NoProfile','-ExecutionPolicy','Bypass','-File',
  'C:\Users\<用户名>\Desktop\hermes-agent-main\.build\workbench\97-powerprobe.ps1'
)
'launcher done'
