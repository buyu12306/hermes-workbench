#!/usr/bin/env python
"""Compose the beautified "Hermes workbench" icon.

Reuses the repo's icon system (scripts/generate_icons.py): the dark squircle
plate + the white nous-girl portrait, plus the product's own ring design tuned
to the Hermes brand gold (default skin: gold and kawaii). Renders a vector SVG
and rasterizes every ICO frame from it.

Outputs (in .build/workbench/): workbench-icon.svg, wb-<size>.png, workbench.ico
"""
import io
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(r"C:/Users/<用户名>/Desktop/hermes-agent-main")
OUT = REPO / ".build" / "workbench"
sys.path.insert(0, str(REPO / "scripts"))

import resvg_py  # noqa: E402
from PIL import Image  # noqa: E402

import generate_icons as gi  # noqa: E402   (module, guarded main)

BG = "squircle-dark.svg"
GIRL = "white"
FRACTION = gi.BORDER_FRACTION  # 0.0407747197 — the product's ring thickness

RING_STOPS = [
    (0.00, "#FFE9A3"),   # pale gold, top highlight
    (0.30, "#FFD700"),   # hermes gold
    (0.55, "#F5C518"),
    (0.78, "#C8961E"),   # light-theme goldenrod
    (1.00, "#8C6A16"),   # shadowed bronze at the bottom
]


def compose(art: gi.IconArt, girl: str, bg: str, thickness_fraction: float,
            ring_stops, glow: bool) -> str:
    inner, w, h = gi.background_inner(art, bg)
    background = ET.fromstring(f"<g>{inner}</g>")
    tile = background.find("{http://www.w3.org/2000/svg}rect")
    assert tile is not None
    geometry = {k: float(tile.attrib[k]) for k in ("x", "y", "width", "height", "rx")}
    silhouette = ET.Element("rect", {k: str(v) for k, v in geometry.items()})
    bottom = geometry["y"] + geometry["height"]
    thickness = geometry["width"] * thickness_fraction
    inset = {"x": 1, "y": 1, "width": -2, "height": -2, "rx": -1}
    for k, v in geometry.items():
        tile.set(k, str(v + inset[k] * thickness / 2))
    tile.set("stroke", "url(#ring)")
    tile.set("stroke-width", str(thickness))
    join_bottom = bottom - thickness + 10
    inner_svg = "".join(ET.tostring(child, encoding="unicode") for child in background)
    clip = ET.tostring(silhouette, encoding="unicode")
    portrait = gi.portrait_layer(art, girl, bg, join_bottom)
    portrait_svg = ET.tostring(portrait, encoding="unicode")

    stops = "".join(
        f'<stop offset="{off}" stop-color="{color}"/>' for off, color in ring_stops
    )
    glow_defs = ""
    glow_svg = ""
    if glow:
        glow_defs = f'''
    <radialGradient id="halo" cx="0.5" cy="0.46" r="0.55">
      <stop offset="0" stop-color="#FFD700" stop-opacity="0.34"/>
      <stop offset="0.55" stop-color="#FFBF00" stop-opacity="0.10"/>
      <stop offset="1" stop-color="#FFBF00" stop-opacity="0"/>
    </radialGradient>'''
        glow_svg = f'<rect x="{geometry["x"]}" y="{geometry["y"]}" width="{geometry["width"]}" height="{geometry["height"]}" rx="{geometry["rx"]}" fill="url(#halo)"/>'

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}">\n'
        f"  <defs>\n"
        f'    <linearGradient id="ring" x1="0" y1="0" x2="0" y2="1">{stops}</linearGradient>'
        f"{glow_defs}\n"
        f'    <clipPath id="icon-silhouette">{clip}</clipPath>\n'
        f"  </defs>\n"
        f"  {inner_svg}\n"
        f'  <g clip-path="url(#icon-silhouette)">{portrait_svg}</g>\n'
        f"  {glow_svg}\n"
        f"</svg>\n"
    )


def render(svg: str, size: int) -> Image.Image:
    data = resvg_py.svg_to_bytes(svg_string=svg, width=size, height=size)
    return Image.open(io.BytesIO(bytes(data))).convert("RGBA")


def main() -> None:
    out_dir = OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    art = gi.IconArt(REPO)
    svg = compose(art, GIRL, BG, FRACTION, RING_STOPS, glow=False)
    (out_dir / "workbench-icon.svg").write_text(svg, encoding="utf-8")

    sizes = [1024, 512, 256, 128, 64, 48, 32, 24, 16]
    frames = {}
    for size in sizes:
        im = render(svg, size)
        frames[size] = im
        im.save(out_dir / f"wb-{size}.png")
    frames[256].save(out_dir / "workbench.ico", format="ICO",
                     sizes=[(s, s) for s in (256, 128, 64, 48, 32, 24, 16)])
    # Zoomed contact sheet for small-size legibility checks (x8 nearest).
    sheet = Image.new("RGBA", (16 * 8 + 32 * 8 + 48 * 8 + 3 * 16, 48 * 8), (60, 60, 70, 255))
    x = 0
    for size in (16, 32, 48):
        im = frames[size].resize((size * 8, size * 8), Image.NEAREST)
        sheet.paste(im, (x, 0), im)
        x += size * 8 + 16
    sheet.save(out_dir / "wb-small-zoom.png")
    print("frames:", sizes)
    print("ico:", out_dir / "workbench.ico")


if __name__ == "__main__":
    main()
