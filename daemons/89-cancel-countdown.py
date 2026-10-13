# -*- coding: utf-8 -*-
"""89-cancel-countdown.py — 取消当前挂起的关机倒计时（应急）

用途：88-watch-shutdown.py 误触/需要继续工作时紧急取消。
机制：shutdown.exe -a + 按命令行匹配终止 88 守护进程（不再用硬编码 PID）。
常规通道：90-keepawake.cmd cancel-shutdown（同样逻辑已内置）。
"""
import subprocess
import time

print('== 尝试取消关机倒计时 ==')
r = subprocess.run(['shutdown.exe', '-a'], capture_output=True, text=True)
print('rc =', r.returncode)
print('stdout:', (r.stdout or '').strip())
print('stderr:', (r.stderr or '').strip())

print('== 终止 88 守护进程（按命令行匹配，不用硬编码 PID）==')
r2 = subprocess.run(
    ['powershell', '-NoProfile', '-Command',
     "Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python(w)?\\.exe' -and $_.CommandLine -match '88-watch-shutdown\\.py' } | "
     "ForEach-Object { 'killing pid ' + $_.ProcessId; Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; 'done'"],
    capture_output=True, text=True)
print('rc =', r2.returncode)
print((r2.stdout or r2.stderr or '').strip())

print('== 复核：是否还有挂起关机 ==')
time.sleep(1)
r3 = subprocess.run(['shutdown.exe', '-a'], capture_output=True, text=True)
print('rc =', r3.returncode)
print('stdout:', (r3.stdout or '').strip())
print('stderr:', (r3.stderr or '').strip())
print('说明：rc=1116（或提示“没有正在进行的关机/无法中止”）= 本来就没有挂起的关机；'
      'rc=0 = 取消成功。')
