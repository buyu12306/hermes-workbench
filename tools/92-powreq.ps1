# 92-powreq.ps1 — dump current power requests (needs elevation). Writes UTF-8 output.
$out = Join-Path $env:LOCALAPPDATA 'hermes\cache\scratch\powreq.txt'
New-Item -ItemType Directory -Force -Path (Split-Path $out) | Out-Null
"The reading time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-File -FilePath $out -Encoding utf8
powercfg /requests 2>&1 | Out-File -FilePath $out -Encoding utf8 -Append
powercfg /lastwake 2>&1 | Out-File -FilePath $out -Encoding utf8 -Append
Add-Content -Path $out -Value '=== done ===' -Encoding utf8
