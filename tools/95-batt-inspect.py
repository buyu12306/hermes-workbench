# -*- coding: utf-8 -*-
"""95-batt-inspect.py — inspect + parse battery report Recent Usage table."""
import re
import pathlib

p = pathlib.Path(r'C:\Users\<用户名>\AppData\Local\hermes\cache\scratch\battreport.html')
h = p.read_text(encoding='utf-8', errors='replace')

# locate the recent usage section
for key in ('最近使用情况', 'Recent usage', '最近使用'):
    i = h.find(key)
    if i >= 0:
        print('found key %r at %d' % (key, i))
        print(h[i:i + 2600])
        break
else:
    print('section not found; dumping title area')
    print(h[:2000])

print()
print('=== generic row parse ===')
rows = re.findall(r'<(?:td|TD)[^>]*>\s*(20\d\d-\d\d-\d\d \d\d:\d\d:\d\d)\s*</(?:td|TD)>\s*<(?:td|TD)[^>]*>(.*?)</(?:td|TD)>\s*<(?:td|TD)[^>]*>(.*?)</(?:td|TD)>', h, re.S | re.I)
print('parsed rows:', len(rows))
for ts, b, c in rows[-80:]:
    b = re.sub(r'<[^>]+>', '', b).strip()
    c = re.sub(r'<[^>]+>', '', c).strip()
    print(ts, '|', b, '|', c)
