# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Adaptadores de macOS (pyobjc): portapapeles, Accesibilidad, Quartz y LaunchAgent.

Ver `paste_photo/platforms/CLAUDE.md`.
"""

from __future__ import annotations

import logging
from contextlib import nullcontext

log = logging.getLogger(__name__)


class MacOSFactory:
    name = "macos"

    def __init__(self) -> None:
        self._windows = None
        self._windows_ready = False

    def create_screenshot_source(self):
        from paste_photo.platforms.macos.sources import MacScreenshotSource

        return MacScreenshotSource()

    def create_window_system(self):
        if not self._windows_ready:
            self._windows_ready = True
            try:
                from paste_photo.platforms.macos.accessibility import MacWindowSystem, is_trusted

                if not is_trusted(prompt=True):  # abre el aviso del sistema la primera vez
                    log.warning("Falta el permiso de Accesibilidad: sin control de ventanas ni "
                                "teclas; funcionan la extensión del navegador, iTerm2, tmux, "
                                "kitty y WezTerm (paste-photo doctor)")
                self._windows = MacWindowSystem()
            except Exception:
                log.exception("No se pudo iniciar el acceso a las ventanas")
        return self._windows

    def create_focus_manager(self):
        from paste_photo.platforms.macos.accessibility import MacFocus

        return MacFocus(self.create_window_system())

    def create_keyboard(self):
        from paste_photo.platforms.macos.keyboard import MacKeyboard

        return MacKeyboard()

    def create_autostart(self):
        from paste_photo.platforms.macos.autostart import LaunchAgentAutostart

        return LaunchAgentAutostart()

    def worker_context(self):
        # Cada llamada a AppKit/AX abre su propio `autorelease_pool` (bucles largos).
        return nullcontext()
