# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Conversión de imágenes para los eventos de captura (Pillow)."""

from __future__ import annotations

import functools
import io
from collections.abc import Callable


def cached(loader: Callable[[], bytes]) -> Callable[[], bytes]:
    """Envuelve un cargador para que solo trabaje la primera vez."""
    return functools.cache(loader)


def dib_to_png(dib: bytes) -> bytes:
    """`CF_DIB` del portapapeles de Windows → PNG."""
    from PIL import BmpImagePlugin

    image = BmpImagePlugin.DibImageFile(io.BytesIO(dib))
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def to_png(data: bytes) -> bytes:
    """Cualquier formato que entienda Pillow → PNG (devuelve tal cual si ya es PNG)."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return data
    from PIL import Image

    out = io.BytesIO()
    Image.open(io.BytesIO(data)).save(out, format="PNG")
    return out.getvalue()
