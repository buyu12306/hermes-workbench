# 84-wol-enable.ps1 — one-shot elevated helper: arm the Intel Wi-Fi NIC as a system wake source.
$out = 'C:\Users\<用户名>\AppData\Local\hermes\cache\scratch\wol_enable.txt'
'== 84-wol-enable run ' + (Get-Date -Format s) + ' ==' | Out-File -Encoding utf8 $out
'--- deviceenablewake attempt ---' | Out-File -Append -Encoding utf8 $out
powercfg /deviceenablewake "Intel(R) Wi-Fi 6 AX201 160MHz" *>> $out
'--- wake_armed after ---' | Out-File -Append -Encoding utf8 $out
powercfg /devicequery wake_armed *>> $out
'--- wake_programmable after ---' | Out-File -Append -Encoding utf8 $out
powercfg /devicequery wake_programmable *>> $out
'== done ==' | Out-File -Append -Encoding utf8 $out
