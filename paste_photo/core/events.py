# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Eventos del dominio. Las interfaces (bandeja, consola...) se suscriben a ellos."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ScreenshotCaptured:
    """Se ha detectado una captura nueva.

    `image_hash` identifica el contenido (sirve para deduplicar) y `timestamp`
    es un instante monotónico en segundos.
    """

    image_hash: str
    timestamp: float
    # Carga perezosa de la imagen en PNG: solo la piden los destinos que pegan sin el
    # portapapeles del SO (p. ej. la extensión del navegador). Codificar una captura 4K a
    # PNG cuesta, así que la fuente la cachea y solo se hace si hace falta.
    load_png: Callable[[], bytes] | None = field(default=None, compare=False, repr=False)

    def png(self) -> bytes | None:
        return self.load_png() if self.load_png is not None else None


@dataclass(frozen=True)
class Pasted:
    """La captura se pegó en `target` (tipo de destino) / `label` (pestaña o ventana)."""

    image_hash: str
    target: str
    label: str


@dataclass(frozen=True)
class NotPasted:
    """Había una captura nueva pero ningún Claude abierto (o falló el pegado en todos)."""

    image_hash: str


@dataclass(frozen=True)
class StateChanged:
    """El servicio se activó o se pausó."""

    active: bool


ServiceEvent = Pasted | NotPasted | StateChanged
