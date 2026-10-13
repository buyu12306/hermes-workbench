# 9A-powercfg-exp.ps1 — test whether non-admin powercfg can toggle AC standby timeout.
# Writes everything to powercfg-exp.txt (utf8).
$out = 'C:\Users\<用户名>\AppData\Local\hermes\cache\scratch\powercfg-exp.txt'
$enc = [Console]::OutputEncoding
[Console]::OutputEncoding = [Text.Encoding]::GetEncoding(936)
$lines = @()
$lines += '=== BEFORE query (STANDBYIDLE) ==='
$lines += (powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE | Out-String)
$lines += '=== /change standby-timeout-ac 0 ==='
$r = (powercfg /change standby-timeout-ac 0 2>&1 | Out-String); $lines += ($r + " exit=$LASTEXITCODE")
Start-Sleep -Milliseconds 400
$lines += '=== AFTER SET query ==='
$lines += (powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE | Out-String)
$lines += '=== RESTORE: try setacvalueindex 300 (5min) ==='
$r = (powercfg /setacvalueindex SCHEME_CURRENT SUB_SLEEP STANDBYIDLE 300 2>&1 | Out-String); $lines += ($r + " exit=$LASTEXITCODE")
$r = (powercfg /setactive SCHEME_CURRENT 2>&1 | Out-String); $lines += ($r + " exit=$LASTEXITCODE")
Start-Sleep -Milliseconds 400
$lines += '=== AFTER RESTORE query ==='
$lines += (powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE | Out-String)
# also capture the whole SUB_SLEEP block for current values (sleep + hibernate timeouts)
$lines += '=== SUB_SLEEP query (full) ==='
$lines += (powercfg /query SCHEME_CURRENT SUB_SLEEP | Out-String)
$lines | Out-File -FilePath $out -Encoding utf8
[Console]::OutputEncoding = $enc
'exp done'
