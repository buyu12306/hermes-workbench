#!/usr/bin/env python
"""Finalize the beautified "Hermes workbench" app/shortcut icon.

Design (variant B of the refinement round — flat modern gold ring):
  - the product's dark squircle plate (#0d1117) + the white nous-girl portrait,
  - a flat Hermes-gold ring using the product's own ring geometry
    (BORDER_FRACTION inward stroke), with an adaptive minimum ring width at
    small sizes so 16/24/32px frames stay crisp,
  - every ICO frame is rendered directly at its target size with resvg
    (vector crisp, no downscale mush).

Outputs: workbench.ico (16..256) + workbench.png (1024) in this directory,
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

BASE_FRACTION = 0.024            # variant B ring weight at >= 64px
MIN_RING_PX = 1.30               # minimum physical ring width in device pixels
FLAT_GOLD = [                    # subtle vertical sheen, reads flat/modern
    (0.0, "#F5C518"),
    (0.5, "#EFB90E"),
    (1.0, "#D9A50F"),
]

ICO_SIZES = [256, 128, 64, 48, 32, 24, 16]


def compose(art: gi.IconArt, thickness_fraction: float) -> str:
    inner, w, h = gi.background_inner(art, BG)
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
    inner_svg = "".join(ET.tostring(child, encoding="unicode") for child in background)
    clip = ET.tostring(silhouette, encoding="unicode")
    portrait = gi.portrait_layer(art, GIRL, BG, bottom - thickness + 10)
    stops = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in FLAT_GOLD)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}">\n'
        f'  <defs><linearGradient id="ring" x1="0" y1="0" x2="0" y2="1">{stops}</linearGradient>'
        f'<clipPath id="icon-silhouette">{clip}</clipPath></defs>\n'
        f"  {inner_svg}\n"
        f'  <g clip-path="url(#icon-silhouette)">{ET.tostring(portrait, encoding="unicode")}</g>\n'
        f"</svg>\n"
    )


def render(svg: str, size: int) -> Image.Image:
    data = resvg_py.svg_to_bytes(svg_string=svg, width=size, height=size)
    return Image.open(io.BytesIO(bytes(data))).convert("RGBA")


def main() -> None:
    art = gi.IconArt(REPO)
    frames = {}
    for size in ICO_SIZES:
        fraction = max(BASE_FRACTION, MIN_RING_PX / size)
        frames[size] = render(compose(art, fraction), size)

    base = frames[256]
    base.save(OUT / "workbench.ico", format="ICO",
              sizes=[(s, s) for s in ICO_SIZES],
              append_images=[frames[s] for s in ICO_SIZES if s != 256])

    master = render(compose(art, BASE_FRACTION), 1024)
    master.save(OUT / "workbench-1024.png")

    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(OUT / "workbench.ico", FINAL_DIR / "hermes-workbench.ico")
    shutil.copy2(OUT / "workbench-1024.png", FINAL_DIR / "hermes-workbench.png")

    # preview sheet: large + small frames on light and dark backgrounds
    sheet = Image.new("RGBA", (560 + 16 + 260 + 16 + 150, 560), (245, 245, 248, 255))
    big = master.resize((560, 560), Image.LANCZOS)
    sheet.alpha_composite(big, (0, 0))
    dark = Image.new("RGBA", (260, 560), (32, 32, 36, 255))
    for i, s in enumerate((128, 64, 32, 16)):
        dark.alpha_composite(frames[s], (16, 10 + i * 140))
    sheet.alpha_composite(dark, (576, 0))
    light = Image.new("RGBA", (150, 560), (255, 255, 255, 255))
    for i, s in enumerate((128, 64, 32, 16)):
        shown = frames[s]
        light.alpha_composite(shown, (16, 10 + i * 140))
    sheet.alpha_composite(light, (852, 0))
    sheet.save(OUT / "final-preview.png")
    print("frames:", ICO_SIZES)
    print("wrote", OUT / "workbench.ico", OUT / "workbench-1024.png", OUT / "final-preview.png")
    print("copied to", FINAL_DIR)


if __name__ == "__main__":
    main()
