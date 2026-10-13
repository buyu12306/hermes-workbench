$procs = Get-Process | Where-Object { $_.ProcessName -eq 'Hermes' }
$t1 = @{}
foreach ($p in $procs) { $t1[$p.Id] = $p.TotalProcessorTime.TotalSeconds }
Start-Sleep -Seconds 6
$rows = @()
$total = 0.0
foreach ($p in (Get-Process | Where-Object { $_.ProcessName -eq 'Hermes' })) {
  $delta = $p.TotalProcessorTime.TotalSeconds - $t1[$p.Id]
  $pct = [math]::Round($delta / 6 * 100, 1)
  $total += $pct
  $cl = (Get-CimInstance Win32_Process -Filter "ProcessId=$($p.Id)" -ErrorAction SilentlyContinue).CommandLine
  $t = 'other'
  if ($cl -match '--type=([a-z\-]+)') { $t = $Matches[1] } elseif ($cl) { $t = 'main' }
  $rows += "$t=$pct"
}
Write-Output ("total=" + [math]::Round($total, 1) + "%  |  " + ($rows -join "  "))
