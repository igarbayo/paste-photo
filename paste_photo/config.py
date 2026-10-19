"""Carga de `config.toml` con valores por defecto sensatos."""

from __future__ import annotations

import os
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CONFIG_FILENAME = "config.toml"


@dataclass(frozen=True)
class Config:
    debounce_ms: int = 2000
    restore_focus: bool = True
    targets: list[dict[str, Any]] = field(default_factory=list)
    source: Path | None = None  # de dónde se cargó (None = valores por defecto)


def default_targets(platform: str) -> list[dict[str, Any]]:
    if platform == "windows":
        return [{"type": "windows_terminal"}, {"type": "browser"}]
    return []


def user_config_dir() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home())) / "paste-photo"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "paste-photo"
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "paste-photo"


def find_config(explicit: Path | None = None) -> Path | None:
    """Orden: ruta explícita > ./config.toml > directorio de configuración del usuario."""
    if explicit is not None:
        if not explicit.is_file():
            raise FileNotFoundError(explicit)
        return explicit
    for candidate in (Path.cwd() / CONFIG_FILENAME, user_config_dir() / CONFIG_FILENAME):
        if candidate.is_file():
            return candidate
    return None


def load_config(platform: str, path: Path | None = None) -> Config:
    found = find_config(path)
    if found is None:
        return Config(targets=default_targets(platform))
    data = tomllib.loads(found.read_text(encoding="utf-8"))
    general = data.get("general", {})
    targets = [t for t in data.get("targets", []) if t.get("enabled", True)]
    return Config(
        debounce_ms=int(general.get("debounce_ms", 2000)),
        restore_focus=bool(general.get("restore_focus", True)),
        targets=targets or default_targets(platform),
        source=found,
    )
