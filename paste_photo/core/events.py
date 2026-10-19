"""Eventos del dominio. Las interfaces (bandeja, consola...) se suscriben a ellos."""

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
