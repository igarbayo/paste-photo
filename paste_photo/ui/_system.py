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
