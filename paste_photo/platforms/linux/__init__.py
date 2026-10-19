"""Linux: pendiente. Pistas en `paste_photo/platforms/CLAUDE.md`."""

from __future__ import annotations

_TODO = "Linux aún no está soportado (ver paste_photo/platforms/CLAUDE.md)"


class LinuxFactory:
    name = "linux"

    def create_screenshot_source(self):
        raise NotImplementedError(_TODO)

    def create_focus_manager(self):
        raise NotImplementedError(_TODO)

    def create_keyboard(self):
        raise NotImplementedError(_TODO)
