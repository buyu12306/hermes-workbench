' Hermes Keep-Awake daemon — autostart launcher (windowless)
' Launches 80-task-keepawake.py via pythonw so holds happen only while busy.
' Failures (missing interpreter/script) are appended to logs\keepawake.log,
' because wscript runs windowless and would otherwise fail silently.
Option Explicit
Dim sh, fso, repo, py, script, logp
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
repo = sh.ExpandEnvironmentStrings("%HERMES_REPO%")
If repo = "%HERMES_REPO%" Then repo = sh.ExpandEnvironmentStrings("%USERPROFILE%") & "\Desktop\hermes-agent-main"
py = repo & "\.venv\Scripts\pythonw.exe"
script = repo & "\.build\workbench\80-task-keepawake.py"
logp = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\hermes\logs\keepawake.log"
If Not fso.FileExists(py) Then
  Call note("launcher: pythonw not found: " & py)
  WScript.Quit 1
End If
If Not fso.FileExists(script) Then
  Call note("launcher: script not found: " & script)
  WScript.Quit 1
End If
sh.CurrentDirectory = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\hermes"
sh.Run """" & py & """ """ & script & """", 0, False
Sub note(msg)
  On Error Resume Next
  Dim f
  Set f = fso.OpenTextFile(logp, 8, True)
  f.WriteLine "launcher " & Now & " " & msg
  f.Close
End Sub
