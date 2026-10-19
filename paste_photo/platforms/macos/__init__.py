# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""macOS: pendiente. Pistas en `paste_photo/platforms/CLAUDE.md`."""

from __future__ import annotations

from contextlib import nullcontext

_TODO = "macOS aún no está soportado (ver paste_photo/platforms/CLAUDE.md)"


class MacOSFactory:
    name = "macos"

    def create_screenshot_source(self):
        raise NotImplementedError(_TODO)

    def create_focus_manager(self):
        raise NotImplementedError(_TODO)

    def create_keyboard(self):
        raise NotImplementedError(_TODO)

    def create_autostart(self):
        raise NotImplementedError(_TODO)

    def worker_context(self):
        return nullcontext()
