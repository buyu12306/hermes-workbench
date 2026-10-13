# 96-kp-xml.ps1 — dump raw XML of the last Kernel-Power events for semantic check.
Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-Kernel-Power'} -MaxEvents 14 |
  ForEach-Object { '----- ' + $_.TimeCreated.ToString('MM-dd HH:mm:ss') + ' id=' + $_.Id; $_.ToXml() } |
  Out-File -FilePath 'C:\Users\<用户名>\AppData\Local\hermes\cache\scratch\kp-xml.txt' -Encoding utf8
'done'
