# wb-gpu-sample.ps1 — per-process GPU utilization over ~6s (WMI perf class; language-independent)
$samples = @()
for ($i = 0; $i -lt 6; $i++) {
  try {
    $rows = Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine -ErrorAction Stop
    foreach ($r in $rows) {
      if ($r.UtilizationPercentage -gt 0) {
        $samples += [pscustomobject]@{ Name = $r.Name; Val = [double]$r.UtilizationPercentage }
      }
    }
  } catch {
    Write-Output "WMI-CLASS-FAIL $($_.Exception.Message)"
    exit 1
  }
  Start-Sleep -Milliseconds 1000
}
# aggregate by pid
$agg = @{}
foreach ($s in $samples) {
  if ($s.Name -match 'pid_(\d+)') {
    $k = [int]$Matches[1]
    if (-not $agg.ContainsKey($k)) { $agg[$k] = 0.0 }
    $agg[$k] += $s.Val
  }
}
$out = @()
foreach ($k in $agg.Keys) {
  $proc = Get-Process -Id $k -ErrorAction SilentlyContinue
  $name = if ($proc) { $proc.ProcessName } else { 'gone' }
  $avg = [math]::Round($agg[$k] / 6, 1)
  if ($avg -ge 2) { $out += [pscustomobject]@{ Pid = $k; Name = $name; GpuPct = $avg } }
}
"TOTAL_TOP:"
$out | Sort-Object GpuPct -Descending | Select-Object -First 10 | Format-Table -AutoSize | Out-String
