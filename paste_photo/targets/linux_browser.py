# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""claude.ai en cualquier navegador de Linux sin la extensión (GNOME Web, Falkon,
qutebrowser... o Firefox/Chromium sin ella): ventana del navegador → foco → Ctrl+V.

Necesita el sistema de ventanas de la sesión (`ctx.windows`: X11, GNOME Shell o KWin).
Como `linux_terminal`, no puede cambiar de pestaña: solo pega si la pestaña de Claude es la
activa de su ventana (el título de la ventana es el de esa pestaña). Al volver a la ventana,
el navegador devuelve el foco al elemento que lo tenía: la imagen va al cursor del prompt
si estaba en él. Con la extensión no hace falta nada de esto (`browser_extension`).
"""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Mapping
from typing import Any

from paste_photo.core.events import ScreenshotCaptured
from paste_photo.core.ports import TargetHandle
from paste_photo.targets._processes import process_name
from paste_photo.targets.browser import DEFAULT_TITLE_REGEX
from paste_photo.targets.registry import TargetContext, register_target

log = logging.getLogger(__name__)

DEFAULT_PASTE_KEYS = "ctrl+v"
# Nombres de proceso (psutil) de los navegadores de Linux.
DEFAULT_BROWSERS = (
    "firefox", "firefox-esr", "firefox-bin", "librewolf", "waterfox", "floorp", "zen",
    "zen-bin", "epiphany", "falkon", "qutebrowser", "konqueror", "midori",
    "chrome", "chromium", "msedge", "brave", "vivaldi-bin", "opera",
)


class LinuxBrowserTarget:
    name = "linux_browser"

    def __init__(self, ctx: TargetContext, *, title_regex: str = DEFAULT_TITLE_REGEX,
                 browsers: tuple[str, ...] = DEFAULT_BROWSERS,
                 paste_keys: str = DEFAULT_PASTE_KEYS, settle_ms: int = 250) -> None:
        self._ctx = ctx
        self._title_re = re.compile(title_regex)
        self._browsers = {b.lower() for b in browsers}
        self._paste_keys = paste_keys
        self._settle_s = settle_ms / 1000

    def locate(self) -> TargetHandle | None:
        if self._ctx.windows is None:
            return None
        windows = [w for w in self._ctx.windows.list_windows()
                   if self._title_re.search(w.title) and process_name(w.pid) in self._browsers]
        if not windows:
            return None
        windows.sort(key=lambda w: self._ctx.recency.last_seen(w.id), reverse=True)
        best = windows[0]
        return TargetHandle(best.id, best.title, {"pid": best.pid})

    def paste(self, handle: TargetHandle, shot: ScreenshotCaptured | None = None) -> None:
        assert self._ctx.windows is not None
        self._ctx.windows.activate(handle.window_id)
        time.sleep(self._settle_s)
        self._ctx.keyboard.send_hotkey(self._paste_keys)
        time.sleep(self._settle_s)


@register_target("linux_browser", platforms=("linux",))
def build(options: Mapping[str, Any], ctx: TargetContext) -> LinuxBrowserTarget:
    return LinuxBrowserTarget(
        ctx,
        title_regex=options.get("title_regex", DEFAULT_TITLE_REGEX),
        browsers=tuple(options.get("browsers", DEFAULT_BROWSERS)),
        paste_keys=options.get("paste_keys", DEFAULT_PASTE_KEYS),
        settle_ms=int(options.get("settle_ms", 250)),
    )
