"""Region luminance sampler for the workbench background iterations."""
import sys
from PIL import Image

REGIONS = {
    "rail_left":      (0.02, 0.35, 0.15, 0.88),
    "bottom_left":    (0.03, 0.86, 0.24, 0.97),
    "top_left":       (0.02, 0.03, 0.18, 0.16),
    "top_right":      (0.82, 0.03, 0.98, 0.20),
    "right_margin":   (0.90, 0.30, 0.995, 0.70),
    "bottom_right":   (0.80, 0.74, 0.97, 0.94),
    "center_col":     (0.45, 0.45, 0.55, 0.60),
    "statusbar":      (0.45, 0.965, 0.70, 0.995),
}

def sample(path):
    img = Image.open(path).convert("RGB")
    w, h = img.size
    out = {}
    for name, (x1, y1, x2, y2) in REGIONS.items():
        box = (int(x1 * w), int(y1 * h), int(x2 * w), int(y2 * h))
        crop = img.crop(box)
        px = list(crop.getdata())
        n = len(px)
        r = sum(p[0] for p in px) / n
        g = sum(p[1] for p in px) / n
        b = sum(p[2] for p in px) / n
        lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
        out[name] = (round(lum, 1), (round(r, 1), round(g, 1), round(b, 1)))
    return out, (w, h)

paths = sys.argv[1:]
results = {}
for p in paths:
    try:
        results[p.split("/")[-1]] = sample(p)
    except Exception as e:
        results[p.split("/")[-1]] = f"ERR {e}"

header = "region".ljust(16) + "".join(k[:20].ljust(22) for k in results)
print(header)
print("-" * len(header))
names = list(REGIONS)
for name in names:
    row = name.ljust(16)
    for k, v in results.items():
        if isinstance(v, str):
            row += v[:20].ljust(22)
        else:
            lum, rgb = v[0][name]
            row += f"{lum:6.1f} {str(rgb):14}".ljust(22)
    print(row)
print()
for k, v in results.items():
    if not isinstance(v, str):
        print(k, "size", v[1])
