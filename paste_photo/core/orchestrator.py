"""Caso de uso: ante una captura, encontrar Claude y pegarla."""

from __future__ import annotations

import logging
from collections import OrderedDict
from collections.abc import Sequence

from paste_photo.core.events import NotPasted, Pasted, ScreenshotCaptured
from paste_photo.core.ports import FocusManager, TargetHandle, TargetStrategy, preserve_focus
from paste_photo.core.recency import Recency

log = logging.getLogger(__name__)

PREFER_RECENT = "recent"
PREFER_ORDER = "order"


class Orchestrator:
    """Elige dónde pegar cada captura.

    - `prefer="recent"` (por defecto): pregunta a todos los destinos y gana el Claude cuya
      ventana usaste por última vez; el orden de `config.toml` solo desempata.
    - `prefer="order"`: Chain of Responsibility pura, gana el primer destino de la config.
    Si un destino falla al pegar, se prueba el siguiente candidato.

    Cada imagen (por hash) se pega **una sola vez**: otras apps (gestores de portapapeles,
    dictado, la propia herramienta de recortes) vuelven a dejar la misma imagen en el
    portapapeles minutos después, y el usuario ya la tuvo (o la quitó a propósito).
    """

    def __init__(
        self,
        targets: Sequence[TargetStrategy],
        focus: FocusManager,
        *,
        recency: Recency | None = None,
        prefer: str = PREFER_RECENT,
        remember_images: int = 100,
        restore_focus: bool = True,
    ) -> None:
        self._targets = list(targets)
        self._focus = focus
        self._recency = recency or Recency()
        self.prefer = prefer  # valida
        self._restore_focus = restore_focus
        self._remember = max(1, remember_images)
        self._seen: OrderedDict[str, None] = OrderedDict()

    @property
    def prefer(self) -> str:
        return self._prefer

    @prefer.setter
    def prefer(self, value: str) -> None:
        if value not in (PREFER_RECENT, PREFER_ORDER):
            raise ValueError(f"prefer debe ser {PREFER_RECENT!r} u {PREFER_ORDER!r}: {value!r}")
        self._prefer = value

    def handle(self, event: ScreenshotCaptured) -> Pasted | NotPasted | None:
        """Procesa una captura. None = imagen ya vista (se ignora en silencio)."""
        short = event.image_hash[:8]
        if event.image_hash in self._seen:
            self._seen.move_to_end(event.image_hash)
            log.debug("Imagen %s ya procesada antes: se ignora", short)
            return None
        self._mark_seen(event.image_hash)

        for target, handle in self.candidates():
            log.info("Pegando imagen %s en %s (%s)", short, target.name, handle.label)
            try:
                if self._restore_focus:
                    with preserve_focus(self._focus):
                        target.paste(handle)
                else:
                    target.paste(handle)
            except Exception:
                log.exception("Error pegando en %s; se prueba el siguiente", target.name)
                continue
            return Pasted(event.image_hash, target.name, handle.label)

        log.info("Imagen %s: no se pudo pegar en ninguna sesión de Claude", short)
        return NotPasted(event.image_hash)

    def candidates(self) -> list[tuple[TargetStrategy, TargetHandle]]:
        """Destinos con Claude abierto, en el orden en que se intentará pegar."""
        found: list[tuple[int, TargetStrategy, TargetHandle]] = []
        for order, target in enumerate(self._targets):
            try:
                handle = target.locate()
            except Exception:
                log.exception("Error localizando el destino %s", target.name)
                continue
            if handle is None:
                continue
            found.append((order, target, handle))
        if self._prefer == PREFER_RECENT:
            found.sort(key=lambda f: (-self._recency.last_seen(f[2].window_id), f[0]))
        return [(target, handle) for _order, target, handle in found]

    def _mark_seen(self, image_hash: str) -> None:
        self._seen[image_hash] = None
        while len(self._seen) > self._remember:
            self._seen.popitem(last=False)
