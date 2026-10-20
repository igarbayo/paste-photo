# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Pequeñas utilidades de escritorio multiplataforma para las interfaces."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def open_path(path: Path) -> None:
    """Abre un archivo con la aplicación predeterminada del sistema."""
    if sys.platform == "win32":
        os.startfile(path)  # noqa: S606 - ruta propia, no entrada del usuario
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def hide_dock_icon() -> None:
    """macOS: app de la barra de menús, sin icono en el Dock ni menú de app. En otros SO no
    hace nada."""
    if sys.platform != "darwin":
        return
    try:
        from AppKit import NSApplication, NSApplicationActivationPolicyAccessory

        NSApplication.sharedApplication().setActivationPolicy_(
            NSApplicationActivationPolicyAccessory)
    except Exception:  # sin pyobjc la bandeja tampoco funcionaría: que falle allí
        pass
