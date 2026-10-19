"""Recursos empaquetados (config por defecto, iconos). Funcionan también dentro del .exe."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

DEFAULT_CONFIG = "default_config.toml"
ICON_PNG = "icon.png"
ICON_ICO = "icon.ico"


def read_text(name: str) -> str:
    return resources.files(__package__).joinpath(name).read_text(encoding="utf-8")


def path(name: str) -> Path:
    """Ruta en disco de un recurso (en el .exe de PyInstaller también es un archivo real)."""
    return Path(str(resources.files(__package__).joinpath(name)))
