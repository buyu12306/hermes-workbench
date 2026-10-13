#!/usr/bin/env python
"""Finalize the beautified "Hermes workbench" app/shortcut icon (round 2).

Design:
  - the product's dark squircle plate (#0d1117) + the white nous-girl portrait,
  - a flat Hermes-gold ring using the product's ring geometry, drawn ON TOP of
    the portrait so the gold edge stays continuous (the girl joins it from
    inside instead of interrupting it),
  - adaptive ring width: max(2.4%, 1.5px) so 16/24/32px frames stay crisp,
    with a brighter gradient below 48px (no dark bronze end at tiny sizes),
  - below 48px the portrait is enlarged ~12% about the bottom so facial
    features survive at 16-32px,
  - every ICO frame is rendered directly at its target size with resvg.

Outputs: workbench.ico (16..256) + workbench-1024.png in this directory,
then copied into %LOCALAPPDATA%/hermes/icons/.
"""
import io
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(r"C:/Users/<用户名>/Desktop/hermes-agent-main")
OUT = REPO / ".build" / "workbench"
FINAL_DIR = Path(r"C:/Users/<用户名>/AppData/Local/hermes/icons")
sys.path.insert(0, str(REPO / "scripts"))

import resvg_py  # noqa: E402
from PIL import Image  # noqa: E402

import generate_icons as gi  # noqa: E402

BG = "squircle-dark.svg"
GIRL = "white"

BASE_FRACTION = 0.024            # ring weight at >= 64px
# Heavier ring where pixels are scarce (a 1.5px stroke still greys out); the
# default minimum below 64px is 1.5px, these sizes get a deliberate weight.
MIN_RING_PX = {16: 1.9, 24: 1.9, 32: 1.6}
SMALL_ZOOM = 1.12                # portrait enlargement below 48px

GOLD = [                         # >= 48px: subtle vertical sheen (flat modern)
    (0.0, "#F5C518"),
    (0.5, "#EFB90E"),
    (1.0, "#D9A50F"),
]
GOLD_SMALL = [                   # < 48px: brighter, no dark end
    (0.0, "#FFD84E"),
    (0.5, "#F5C518"),
    (1.0, "#E0AE12"),
]

ICO_SIZES = [256, 128, 64, 48, 32, 24, 16]


def zoomed_box(zoom: float) -> tuple[float, float, float, float]:
    """The registered girl box scaled about its bottom-center (keeps the join)."""
    x, y, w, h = gi.GIRL_BOXES[BG]
    cx, yb = x + w / 2, y + h
    return (cx - w * zoom / 2, yb - h * zoom, w * zoom, h * zoom)


def portrait_svg(art: gi.IconArt, box: tuple[float, float, float, float], join_bottom: float) -> str:
    portrait = ET.fromstring(gi.girl_layer(art, GIRL, box, align="xMidYMax"))
    _, y, pw, ph = box
    _, by, bw, bh = gi.girl_bbox(art, GIRL)
    scale = min(pw / bw, ph / bh)
    gi.drag_bottom_nodes(portrait[0], cutoff=by + bh * 0.97, band=bh * 0.02,
                         distance=max(0.0, join_bottom - (y + ph)) / scale)
    portrait.set("overflow", "visible")
    return ET.tostring(portrait, encoding="unicode")


def compose(art: gi.IconArt, thickness_fraction: float, zoom: float, stops) -> str:
    inner, w, h = gi.background_inner(art, BG)
    background = ET.fromstring(f"<g>{inner}</g>")
    tile = background.find("{http://www.w3.org/2000/svg}rect")
    assert tile is not None
    geometry = {k: float(tile.attrib[k]) for k in ("x", "y", "width", "height", "rx")}
    silhouette = ET.Element("rect", {k: str(v) for k, v in geometry.items()})
    bottom = geometry["y"] + geometry["height"]
    thickness = geometry["width"] * thickness_fraction
    ring_geom = {"x": geometry["x"] + thickness / 2, "y": geometry["y"] + thickness / 2,
                 "width": geometry["width"] - thickness, "height": geometry["height"] - thickness,
                 "rx": geometry["rx"] - thickness / 2}
    inner_svg = "".join(ET.tostring(child, encoding="unicode") for child in background)
    clip = ET.tostring(silhouette, encoding="unicode")
    portrait = portrait_svg(art, zoomed_box(zoom), bottom - thickness + 10)
    grad = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in stops)
    ring_attrs = " ".join(f'{k}="{v}"' for k, v in ring_geom.items())
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}">\n'
        f'  <defs><linearGradient id="ring" x1="0" y1="0" x2="0" y2="1">{grad}</linearGradient>'
        f'<clipPath id="icon-silhouette">{clip}</clipPath></defs>\n'
        f"  {inner_svg}\n"
        f'  <g clip-path="url(#icon-silhouette)">{portrait}</g>\n'
        f'  <rect {ring_attrs} fill="none" stroke="url(#ring)" stroke-width="{thickness}"/>\n'
        f"</svg>\n"
    )


def render(svg: str, size: int) -> Image.Image:
    data = resvg_py.svg_to_bytes(svg_string=svg, width=size, height=size)
    return Image.open(io.BytesIO(bytes(data))).convert("RGBA")


def main() -> None:
    art = gi.IconArt(REPO)
    frames = {}
    for size in ICO_SIZES:
        fraction = max(BASE_FRACTION, MIN_RING_PX.get(size, 1.5) / size)
        stops = GOLD_SMALL if size < 48 else GOLD
        zoom = SMALL_ZOOM if size < 48 else 1.0
        frames[size] = render(compose(art, fraction, zoom, stops), size)
        frames[size].save(OUT / f"frame-{size}.png")

    base = frames[256]
    base.save(OUT / "workbench.ico", format="ICO",
              sizes=[(s, s) for s in ICO_SIZES],
              append_images=[frames[s] for s in ICO_SIZES if s != 256])

    master = render(compose(art, BASE_FRACTION, 1.0, GOLD), 1024)
    master.save(OUT / "workbench-1024.png")

    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(OUT / "workbench.ico", FINAL_DIR / "hermes-workbench.ico")
    shutil.copy2(OUT / "workbench-1024.png", FINAL_DIR / "hermes-workbench.png")

    # preview: large master + small frames at true size on dark and light panels
    sheet = Image.new("RGBA", (560 + 16 + 260 + 16 + 150, 560), (245, 245, 248, 255))
    big = master.resize((560, 560), Image.LANCZOS)
    sheet.alpha_composite(big, (0, 0))
    dark = Image.new("RGBA", (260, 560), (28, 28, 32, 255))
    y = 12
    for s in (128, 64, 48, 32, 24, 16):
        dark.alpha_composite(frames[s], (16, y))
        y += s + 12
    sheet.alpha_composite(dark, (576, 0))
    light = Image.new("RGBA", (150, 560), (255, 255, 255, 255))
    y = 12
    for s in (128, 64, 48, 32, 24, 16):
        light.alpha_composite(frames[s], (16, y))
        y += s + 12
    sheet.alpha_composite(light, (852, 0))
    sheet.save(OUT / "final-preview.png")
    print("frames:", ICO_SIZES)
    print("wrote", OUT / "workbench.ico", OUT / "workbench-1024.png", OUT / "final-preview.png")
    print("copied to", FINAL_DIR)


if __name__ == "__main__":
    main()
