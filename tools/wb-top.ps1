$procs = Get-Process | Sort-Object CPU -Descending | Select-Object -First 10
$t1 = @{}; foreach ($p in $procs) { $t1[$p.Id] = $p.CPU }
Start-Sleep -Seconds 5
$rows = @()
foreach ($p in ($procs | Where-Object { [System.Diagnostics.Process]::GetProcessById($_.Id) })) { }
foreach ($p in (Get-Process | Where-Object { $t1.ContainsKey($_.Id) })) {
  $d = [math]::Round(($p.CPU - $t1[$p.Id]) / 5 * 100, 1)
  if ($d -gt 0) { $rows += ($p.ProcessName + '=' + $d + '%') }
}
$rows -join '  '