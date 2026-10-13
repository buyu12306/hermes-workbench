$rows = Get-Process | Where-Object { $_.ProcessName -match '^(Hermes|hermes|dsh|claude|node|python|pythonw)' } | Select-Object ProcessName, Id, @{n='MemMB';e={[math]::Round($_.WorkingSet64/1MB,1)}}
$rows | Sort-Object MemMB -Descending | Format-Table -AutoSize | Out-String -Width 130
"TOTAL count: " + @($rows).Count
