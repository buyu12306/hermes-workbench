# wb-neighbors.ps1 - top CPU% deltas across ALL processes over 6s (who burns now)
$snap = @{}
foreach ($p in Get-Process) { $snap[$p.Id] = @($p.ProcessName, $p.TotalProcessorTime.TotalSeconds) }
Start-Sleep -Seconds 6
$rows = @()
foreach ($p in Get-Process) {
  if ($snap.ContainsKey($p.Id)) {
    $d = ($p.TotalProcessorTime.TotalSeconds - $snap[$p.Id][1]) / 6 * 100
    if ($d -ge 1.5) { $rows += [pscustomobject]@{ Name = $p.ProcessName; Pid = $p.Id; Pct = [math]::Round($d, 1) } }
  }
}
$rows | Sort-Object Pct -Descending | Format-Table -AutoSize | Out-String
