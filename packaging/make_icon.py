"""Genera los iconos de la app (PNG para la bandeja, ICO para el .exe y el instalador).

Uso: python packaging/make_icon.py   (los escribe en paste_photo/resources/)
Se dibujan por código para que cualquiera pueda regenerarlos o retocarlos sin un editor.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

SIZE = 256
BACKGROUND = (217, 119, 87, 255)  # naranja tipo Claude
FOREGROUND = (255, 255, 255, 255)
OUT = Path(__file__).resolve().parent.parent / "paste_photo" / "resources"


def draw(size: int = SIZE) -> Image.Image:
    s = size / 256  # todo se dibuja en coordenadas de 256 px y se escala
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((8 * s, 8 * s, 248 * s, 248 * s), radius=56 * s, fill=BACKGROUND)

    # Esquinas de una selección de recorte.
    w, a, lo, hi = 18 * s, 54 * s, 52 * s, 204 * s
    for x, y, dx, dy in ((lo, lo, 1, 1), (hi, lo, -1, 1), (lo, hi, 1, -1), (hi, hi, -1, -1)):
        d.rectangle(sorted_box(x, y, x + dx * a, y + dy * w), fill=FOREGROUND)
        d.rectangle(sorted_box(x, y, x + dx * w, y + dy * a), fill=FOREGROUND)

    # Flecha hacia abajo: "se pega sola".
    cx = 128 * s
    d.rectangle((cx - 11 * s, 86 * s, cx + 11 * s, 140 * s), fill=FOREGROUND)
    d.polygon([(cx - 36 * s, 132 * s), (cx + 36 * s, 132 * s), (cx, 172 * s)], fill=FOREGROUND)
    return img


def sorted_box(x0: float, y0: float, x1: float, y1: float) -> tuple[float, float, float, float]:
    return (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    icon = draw()
    icon.save(OUT / "icon.png")
    sizes = [(n, n) for n in (16, 24, 32, 48, 64, 256)]
    icon.save(OUT / "icon.ico", sizes=sizes)
    print(f"Iconos escritos en {OUT}")


if __name__ == "__main__":
    main()
