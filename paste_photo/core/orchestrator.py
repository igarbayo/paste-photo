"""Caso de uso: ante una captura, encontrar Claude Code y pegarla."""

from __future__ import annotations

import logging
from collections.abc import Sequence

from paste_photo.core.events import ScreenshotCaptured
from paste_photo.core.ports import FocusManager, TargetStrategy, preserve_focus

log = logging.getLogger(__name__)


class Orchestrator:
    """Recorre los destinos en orden (Chain of Responsibility); el primero que
    localiza Claude Code recibe la imagen."""

    def __init__(
        self,
        targets: Sequence[TargetStrategy],
        focus: FocusManager,
        *,
        debounce_s: float = 2.0,
        restore_focus: bool = True,
    ) -> None:
        self._targets = list(targets)
        self._focus = focus
        self._debounce_s = debounce_s
        self._restore_focus = restore_focus
        self._last: ScreenshotCaptured | None = None

    def handle(self, event: ScreenshotCaptured) -> str | None:
        """Procesa una captura. Devuelve el nombre del destino usado o None."""
        if self._is_duplicate(event):
            log.debug("Captura duplicada ignorada (%s)", event.image_hash[:8])
            return None
        self._last = event

        for target in self._targets:
            try:
                handle = target.locate()
            except Exception:
                log.exception("Error localizando el destino %s", target.name)
                continue
            if handle is None:
                continue

            log.info("Pegando captura en %s (%s)", target.name, handle.label)
            try:
                if self._restore_focus:
                    with preserve_focus(self._focus):
                        target.paste(handle)
                else:
                    target.paste(handle)
            except Exception:
                log.exception("Error pegando en %s", target.name)
                return None
            return target.name

        log.info("Captura detectada, pero no hay ninguna sesión de Claude Code abierta")
        return None

    def _is_duplicate(self, event: ScreenshotCaptured) -> bool:
        last = self._last
        return (
            last is not None
            and last.image_hash == event.image_hash
            and event.timestamp - last.timestamp < self._debounce_s
        )
