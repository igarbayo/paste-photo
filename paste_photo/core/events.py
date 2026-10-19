from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScreenshotCaptured:
    """Se ha detectado una captura nueva.

    `image_hash` identifica el contenido (sirve para deduplicar) y `timestamp`
    es un instante monotónico en segundos.
    """

    image_hash: str
    timestamp: float
