# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Piezas de escritorio comunes a todas las sesiones de Linux: inicio automático (XDG),
foco basado en el sistema de ventanas y adaptadores nulos cuando la sesión no lo permite."""

from __future__ import annotations

import os
from pathlib import Path

from paste_photo.core.ports import WindowSystem

DESKTOP_ENTRY = """[Desktop Entry]
Type=Application
Name=PastePhoto
Comment=Paste your screenshots into Claude
Exec={command}
Icon=paste-photo
Terminal=false
X-GNOME-Autostart-enabled=true
"""


def autostart_dir() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "autostart"


class XdgAutostart:
    """`~/.config/autostart/paste-photo.desktop`: lo respetan GNOME, KDE, XFCE, Cinnamon..."""

    def __init__(self, folder: Path | None = None) -> None:
        self._file = (folder or autostart_dir()) / "paste-photo.desktop"

    def is_enabled(self) -> bool:
        return self._file.exists()

    def enable(self, command: str) -> None:
        self._file.parent.mkdir(parents=True, exist_ok=True)
        self._file.write_text(DESKTOP_ENTRY.format(command=command), encoding="utf-8")

    def disable(self) -> None:
        self._file.unlink(missing_ok=True)


class WindowFocus:
    """FocusManager sobre cualquier `WindowSystem` (Memento: ventana activa)."""

    def __init__(self, windows: WindowSystem) -> None:
        self._windows = windows

    def capture(self) -> int | None:
        try:
            return self._windows.active_window()
        except Exception:
            return None

    def restore(self, snapshot: int | None) -> None:
        if snapshot:
            try:
                self._windows.activate(snapshot)
            except Exception:
                pass

    def activate(self, window_id: int) -> None:
        self._windows.activate(window_id)


class NullFocus:
    """Sesión sin control de ventanas: no hay nada que guardar ni restaurar."""

    def capture(self) -> None:
        return None

    def restore(self, snapshot: object) -> None:
        pass

    def activate(self, window_id: int) -> None:
        raise RuntimeError("Esta sesión no permite activar ventanas")


class NullKeyboard:
    def __init__(self, reason: str) -> None:
        self._reason = reason

    def send_hotkey(self, hotkey: str) -> None:
        raise RuntimeError(self._reason)
