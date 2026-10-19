# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""claude.ai en cualquier navegador Chromium, a través de la extensión de paste-photo.

No necesita foco, ventanas ni teclas: la extensión inyecta la imagen en el editor de la
pestaña. Por eso funciona igual en Windows, X11 y Wayland, y también en pestañas de fondo.
Si la extensión no está conectada, `locate()` devuelve None y se prueban otros destinos.
"""

from __future__ import annotations

import base64
import logging
from collections.abc import Mapping
from typing import Any

from paste_photo.core.events import ScreenshotCaptured
from paste_photo.core.ports import TargetHandle
from paste_photo.targets.registry import TargetContext, register_target

log = logging.getLogger(__name__)

LIST_TIMEOUT_S = 1.5
PASTE_TIMEOUT_S = 15.0


class BrowserExtensionTarget:
    name = "browser_extension"

    def __init__(self, *, activate: bool = False, server: Any = None) -> None:
        self._activate = activate
        self._server = server  # inyectable en tests; si no, el del proceso

    def _bridge(self):
        if self._server is None:
            from paste_photo.bridge.server import BridgeServer

            self._server = BridgeServer.instance()
        return self._server

    def locate(self) -> TargetHandle | None:
        from paste_photo.bridge.server import BridgeError

        found: list[tuple[float, bool, TargetHandle]] = []
        for client in self._bridge().clients():
            try:
                reply = client.request({"cmd": "list"}, timeout=LIST_TIMEOUT_S)
            except BridgeError as error:
                log.debug("La extensión no respondió: %s", error)
                continue
            for tab in reply.get("tabs", []):
                last_used = float(tab.get("lastUsed") or 0) / 1000  # ms → s (epoch)
                handle = TargetHandle(
                    window_id=0,  # sin ventana del SO: la prioridad usa last_used
                    label=tab.get("title") or tab.get("url", "claude.ai"),
                    extra={"client": client, "tab_id": tab["tabId"], "last_used": last_used},
                )
                found.append((last_used, bool(tab.get("active")), handle))
        if not found:
            return None
        found.sort(key=lambda item: (item[0], item[1]), reverse=True)
        best = found[0][2]
        candidates = [handle for _, _, handle in found]
        return TargetHandle(best.window_id, best.label, {**best.extra, "candidates": candidates})

    def paste(self, handle: TargetHandle, shot: ScreenshotCaptured) -> None:
        png = shot.png()
        if png is None:
            raise RuntimeError("La captura no trae imagen PNG para la extensión")
        payload = base64.b64encode(png).decode("ascii")
        name = f"screenshot-{shot.image_hash[:8]}.png"
        for candidate in handle.extra.get("candidates", [handle]):
            reply = candidate.extra["client"].request(
                {"cmd": "paste", "tabId": candidate.extra["tab_id"], "png": payload,
                 "name": name, "activate": self._activate},
                timeout=PASTE_TIMEOUT_S,
            )
            if reply.get("ok"):
                log.info("Pegada en el navegador: %r", candidate.label)
                return
            log.info("Pestaña %r descartada: %s", candidate.label, reply.get("error"))
        raise RuntimeError("Ninguna pestaña de claude.ai aceptó la imagen")


@register_target("browser_extension")
def build(options: Mapping[str, Any], ctx: TargetContext) -> BrowserExtensionTarget:
    target = BrowserExtensionTarget(activate=bool(options.get("activate", False)))
    # El puente se abre ya al arrancar: la extensión (vía su host nativo) se conecta en
    # segundo plano y está lista antes de la primera captura.
    try:
        target._bridge()
    except OSError as error:
        log.warning("No se pudo abrir el puente con el navegador: %s", error)
    return target
