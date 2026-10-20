# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Genera las imágenes de marca del repositorio a partir del icono de la app.

Uso: python packaging/make_brand.py   (las escribe en docs/assets/)
- logo.png: el icono a 512 px, para la cabecera del README.
- social-preview.png: 1280x640, la imagen que GitHub muestra al compartir el enlace
  (se sube a mano: Settings → General → Social preview).
Texto con la fuente que trae Pillow (Aileron, CC0): se puede regenerar en cualquier SO.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_icon import BACKGROUND, draw  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "docs" / "assets"
WIDTH, HEIGHT = 1280, 640
PAPER = (250, 247, 242, 255)  # fondo claro cálido
INK = (38, 33, 29, 255)  # texto principal
MUTED = (110, 101, 94, 255)  # texto secundario
CHIP = (242, 226, 218, 255)  # fondo de las etiquetas (tono del icono, muy claro)

TITLE = "PastePhoto"
TAGLINE = ("Take a screenshot.", "It shows up in Claude.")
CHIPS = ("Windows · macOS · Linux", "Claude Code in any terminal",
         "claude.ai in Chrome, Edge, Firefox, Safari")


def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.load_default(size)


def logo(size: int = 512) -> Image.Image:
    return draw(size)


def social_preview() -> Image.Image:
    img = Image.new("RGBA", (WIDTH, HEIGHT), PAPER)
    d = ImageDraw.Draw(img)
    # Franja del color del icono a la izquierda y el icono encima.
    d.rectangle((0, 0, 24, HEIGHT), fill=BACKGROUND)
    icon = draw(300)
    img.alpha_composite(icon, (110, (HEIGHT - 300) // 2))

    x = 480
    d.text((x, 150), TITLE, font=font(92), fill=INK, stroke_width=2, stroke_fill=INK)
    for i, line in enumerate(TAGLINE):
        d.text((x, 275 + i * 56), line, font=font(46), fill=MUTED)

    # Etiquetas: qué cubre, en una o dos filas.
    chip_font, pad_x, pad_y, gap = font(26), 20, 10, 14
    ascent, descent = chip_font.getmetrics()
    h = ascent + descent + 2 * pad_y  # misma altura en todas, tengan o no letras con rabo
    cx, cy = x, 425
    for label in CHIPS:
        w = int(d.textlength(label, font=chip_font)) + 2 * pad_x
        if cx + w > WIDTH - 60:
            cx, cy = x, cy + h + gap
        d.rounded_rectangle((cx, cy, cx + w, cy + h), radius=h // 2, fill=CHIP)
        d.text((cx + pad_x, cy + pad_y), label, font=chip_font, fill=INK)
        cx += w + gap
    return img.convert("RGB")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    logo().save(OUT / "logo.png", optimize=True)
    social_preview().save(OUT / "social-preview.png", optimize=True)
    print(f"Imágenes escritas en {OUT}")


if __name__ == "__main__":
    main()
