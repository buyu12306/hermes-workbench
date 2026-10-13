#!/usr/bin/env python
"""Render refined ring variants for the workbench icon and a comparison sheet."""
import io
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(r"C:/Users/<用户名>/Desktop/hermes-agent-main")
OUT = REPO / ".build" / "workbench"
sys.path.insert(0, str(REPO / "scripts"))

import resvg_py  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

import generate_icons as gi  # noqa: E402

BG = "squircle-dark.svg"
GIRL = "white"


def compose(art, *, thickness_fraction, ring_stops, glow=None, tile_tint=None,
            seat=True, join_extra=10):
    inner, w, h = gi.background_inner(art, BG)
    background = ET.fromstring(f"<g>{inner}</g>")
    tile = background.find("{http://www.w3.org/2000/svg}rect")
    geometry = {k: float(tile.attrib[k]) for k in ("x", "y", "width", "height", "rx")}
    silhouette = ET.Element("rect", {k: str(v) for k, v in geometry.items()})
    bottom = geometry["y"] + geometry["height"]
    thickness = geometry["width"] * thickness_fraction
    inset = {"x": 1, "y": 1, "width": -2, "height": -2, "rx": -1}
    for k, v in geometry.items():
        tile.set(k, str(v + inset[k] * thickness / 2))
    tile.set("stroke", "url(#ring)")
    tile.set("stroke-width", str(thickness))
    join_bottom = bottom - thickness + join_extra
    inner_svg = "".join(ET.tostring(child, encoding="unicode") for child in background)
    clip = ET.tostring(silhouette, encoding="unicode")
    portrait_svg = ET.tostring(gi.portrait_layer(art, GIRL, BG, join_bottom), encoding="unicode")

    stops = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in ring_stops)
    defs = [f'<linearGradient id="ring" x1="0" y1="0" x2="0" y2="1">{stops}</linearGradient>']
    body = [inner_svg]
    if glow:
        stops_g = "".join(f'<stop offset="{o}" stop-color="{c}" stop-opacity="{a}"/>'
                          for o, c, a in glow["stops"])
        defs.append(f'<radialGradient id="halo" cx="0.5" cy="{glow["cy"]}" r="{glow["r"]}">{stops_g}</radialGradient>')
        body.append(f'<rect x="{geometry["x"]}" y="{geometry["y"]}" width="{geometry["width"]}" '
                    f'height="{geometry["height"]}" rx="{geometry["rx"]}" fill="url(#halo)"/>')
    body.append(f'<g clip-path="url(#icon-silhouette)">{portrait_svg}</g>')
    if seat:
        # faint inner seat line under the ring so the gold sits ON the plate
        r = {k: str(v + inset[k] * thickness) for k, v in geometry.items()}
        body.append(f'<rect x="{r["x"]}" y="{r["y"]}" width="{r["width"]}" height="{r["height"]}" '
                    f'rx="{r["rx"]}" fill="none" stroke="#000000" stroke-opacity="0.55" '
                    f'stroke-width="{max(2.0, thickness * 0.16)}"/>')
    defs.append(f'<clipPath id="icon-silhouette">{clip}</clipPath>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}">\n'
            f"  <defs>{''.join(defs)}</defs>\n  " + "\n  ".join(body) + "\n</svg>\n")


def render(svg, size):
    data = resvg_py.svg_to_bytes(svg_string=svg, width=size, height=size)
    return Image.open(io.BytesIO(bytes(data))).convert("RGBA")


SOFT_GOLD = [
    (0.00, "#FFE9A3"), (0.28, "#FFD86B"), (0.55, "#F0BE3A"),
    (0.80, "#C99A28"), (1.00, "#9A741B"),
]
FLAT_GOLD = [(0.0, "#F5C518"), (0.5, "#EFB90E"), (1.0, "#D9A50F")]
DEEP_GOLD = [
    (0.00, "#F7DD8E"), (0.35, "#F3C64B"), (0.70, "#D9A62E"), (1.00, "#A17A17"),
]

VARIANTS = {
    # name: kwargs
    "A_thin_soft_24": dict(thickness_fraction=0.024, ring_stops=SOFT_GOLD),
    "B_flat_modern_24": dict(thickness_fraction=0.024, ring_stops=FLAT_GOLD, seat=False),
    "C_thin_soft_glow": dict(thickness_fraction=0.024, ring_stops=SOFT_GOLD, glow=dict(
        cy=0.44, r=0.62, stops=[(0.0, "#FFD700", 0.30), (0.55, "#FFBF00", 0.10), (1.0, "#FFBF00", 0.0)])),
    "D_hairline_18": dict(thickness_fraction=0.018, ring_stops=DEEP_GOLD),
}


def main():
    art = gi.IconArt(REPO)
    panel = 360
    small = [96, 64, 48, 32, 24, 16]
    cols = len(VARIANTS)
    row_h = panel + 16 + sum(s + 8 for s in small)
    sheet = Image.new("RGBA", (cols * (panel + 20) + 20, row_h + 30), (235, 235, 240, 255))
    draw = ImageDraw.Draw(sheet)
    for idx, (name, kwargs) in enumerate(VARIANTS.items()):
        svg = compose(art, **kwargs)
        (OUT / f"variant-{name}.svg").write_text(svg, encoding="utf-8")
        big = render(svg, panel)
        x = 20 + idx * (panel + 20)
        sheet.paste(big, (x, 30), big)
        y = 30 + panel + 16
        for s in small:
            im = render(svg, s)
            sheet.paste(im, (x, y), im)
            y += s + 8
        draw.text((x + 4, 8), name, fill=(20, 20, 20, 255))
    sheet.save(OUT / "variants-sheet.png")
    print("wrote", OUT / "variants-sheet.png", sheet.size)


if __name__ == "__main__":
    main()
