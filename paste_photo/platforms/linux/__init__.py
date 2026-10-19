# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Linux: la familia de adaptadores depende de la sesión (X11, GNOME Wayland, KDE Wayland).

Ver `paste_photo/platforms/CLAUDE.md` y `session.py`.
"""

from __future__ import annotations

import logging
from contextlib import nullcontext

from paste_photo.platforms.linux.desktop import (
    NullFocus,
    NullKeyboard,
    WindowFocus,
    XdgAutostart,
)
from paste_photo.platforms.linux.session import Session, detect

log = logging.getLogger(__name__)


class LinuxFactory:
    name = "linux"

    def __init__(self, session: Session | None = None) -> None:
        self.session = session or detect()
        self._windows = None
        self._windows_ready = False
        self._x = None

    # --- ventanas, foco y teclado ----------------------------------------------------

    def create_window_system(self):
        if not self._windows_ready:
            self._windows_ready = True
            self._windows = self._make_window_system()
        return self._windows

    def _make_window_system(self):
        backend = self.session.backend
        try:
            if backend == "x11":
                from paste_photo.platforms.linux.x11 import X11WindowSystem

                return X11WindowSystem(self._shared_x())
            if backend == "gnome":
                from paste_photo.platforms.linux import gnome

                if gnome.extension_available():
                    return gnome.GnomeShellWindowSystem()
                log.warning("Falta la extensión de GNOME Shell (paste-photo setup gnome): sin "
                            "control de ventanas; funcionan navegador, tmux, kitty y WezTerm.")
                return None
            if backend == "kde":
                from paste_photo.platforms.linux.kde import KWinWindowSystem

                return KWinWindowSystem()
        except Exception:
            log.exception("No se pudo iniciar el sistema de ventanas (%s)", backend)
        return None

    def create_focus_manager(self):
        windows = self.create_window_system()
        return WindowFocus(windows) if windows is not None else NullFocus()

    def create_keyboard(self):
        backend = self.session.backend
        if backend == "x11":
            from paste_photo.platforms.linux.x11 import X11Keyboard

            return X11Keyboard()
        if backend == "gnome" and self.create_window_system() is not None:
            from paste_photo.platforms.linux.gnome import GnomeShellKeyboard

            return GnomeShellKeyboard()
        if backend == "kde":
            from paste_photo.platforms.linux.kde import PortalKeyboard

            return PortalKeyboard()
        return NullKeyboard(f"Esta sesión no permite simular teclas ({self.session.describe()})")

    def _shared_x(self):
        if self._x is None:
            from paste_photo.platforms.linux.x11 import _X

            self._x = _X()
        return self._x

    # --- capturas -------------------------------------------------------------------

    def create_screenshot_source(self):
        from paste_photo.platforms.linux.sources import (
            ScreenshotFolderSource,
            WlPasteWatchSource,
            X11ClipboardSource,
        )

        if self.session.backend == "x11" and not self.session.wayland:
            return X11ClipboardSource()
        if self.session.wayland and WlPasteWatchSource.supported():
            return WlPasteWatchSource()  # KDE, wlroots...
        if self.session.backend == "x11":
            return X11ClipboardSource()  # Wayland sin data-control pero con XWayland
        return ScreenshotFolderSource()  # GNOME Wayland

    # --- resto -------------------------------------------------------------------------

    def create_autostart(self):
        return XdgAutostart()

    def worker_context(self):
        return nullcontext()
