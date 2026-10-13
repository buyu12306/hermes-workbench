# 97-powerprobe.ps1 — elevated power diagnostics (run as admin).
$out = 'C:\Users\<用户名>\AppData\Local\hermes\cache\scratch\powerprobe'
New-Item -ItemType Directory -Force -Path $out | Out-Null
powercfg /requests | Out-File "$out\requests.txt" -Encoding utf8
powercfg /waketimers | Out-File "$out\waketimers.txt" -Encoding utf8
powercfg /a | Out-File "$out\powercap.txt" -Encoding utf8
powercfg /sleepstudy /output "$out\sleepstudy.html" | Out-File "$out\sleepstudy-run.txt" -Encoding utf8
'PROBE-DONE' | Out-File "$out\done.txt" -Encoding utf8
