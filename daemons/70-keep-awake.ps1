param([int]$Minutes = 55)
# keep-awake guard: prevent idle system sleep while a long unattended task runs.
# Usage: powershell.exe -NoProfile -ExecutionPolicy Bypass -File 70-keep-awake.ps1 -Minutes 55
# Reason: idle suspend >~5 min freezes kanban workers mid-run; on resume the session-turn
# lease cannot refresh and the worker exits rc=130 (see skill hermes-workbench-build).
$sig = @'
using System;
using System.Runtime.InteropServices;
public static class SleepGuard {
  [DllImport("kernel32.dll", SetLastError = true)]
  public static extern uint SetThreadExecutionState(uint esFlags);
  public static void KeepAwake() { SetThreadExecutionState(0x80000001u); } // CONTINUOUS | SYSTEM_REQUIRED
  public static void Release()   { SetThreadExecutionState(0x80000000u); } // CONTINUOUS
}
'@
Add-Type -TypeDefinition $sig
# NOTE: keep the numeric flags INSIDE the C# class — PowerShell 5.1 parses 0x80000000 as a
# negative Int32 and [uint32] casts of it throw (learned the hard way 2026-10-09).
$end = (Get-Date).AddMinutes($Minutes)
Write-Output ("keep-awake active for {0} min (until {1})" -f $Minutes, $end.ToString("HH:mm:ss"))
while ((Get-Date) -lt $end) {
  [SleepGuard]::KeepAwake()
  Start-Sleep -Seconds 40
}
[SleepGuard]::Release()
Write-Output ("keep-awake released after {0} min" -f $Minutes)
