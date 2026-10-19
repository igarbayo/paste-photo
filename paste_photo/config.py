"""Carga y guardado de la configuración (`config.toml`).

Una sola fuente de valores por defecto: `resources/default_config.toml`, que también es la
plantilla que se copia al directorio del usuario la primera vez.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from paste_photo import resources
from paste_photo.paths import CONFIG_FILENAME, user_config_dir, user_config_file


@dataclass(frozen=True)
class Config:
    remember_images: int = 100
    prefer: str = "recent"  # "recent" | "order"
    restore_focus: bool = True
    notify: bool = True  # notificaciones de la bandeja al pegar
    targets: list[dict[str, Any]] = field(default_factory=list)
    source: Path | None = None  # de dónde se cargó (None = valores por defecto empaquetados)


def default_targets(platform: str) -> list[dict[str, Any]]:
    if platform == "windows":
        return [{"type": "windows_terminal"}, {"type": "browser"}]
    return []


def find_config(explicit: Path | None = None) -> Path | None:
    """Orden: ruta explícita > ./config.toml (desarrollo) > directorio del usuario."""
    if explicit is not None:
        if not explicit.is_file():
            raise FileNotFoundError(explicit)
        return explicit
    for candidate in (Path.cwd() / CONFIG_FILENAME, user_config_dir() / CONFIG_FILENAME):
        if candidate.is_file():
            return candidate
    return None


def ensure_user_config() -> Path:
    """Crea el config del usuario a partir de la plantilla si aún no existe."""
    target = user_config_file()
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(resources.read_text(resources.DEFAULT_CONFIG), encoding="utf-8")
    return target


def parse_config(text: str, platform: str, source: Path | None = None) -> Config:
    data = tomllib.loads(text)
    general = data.get("general", {})
    targets = [t for t in data.get("targets", []) if t.get("enabled", True)]
    return Config(
        remember_images=int(general.get("remember_images", 100)),
        prefer=str(general.get("prefer", "recent")),
        restore_focus=bool(general.get("restore_focus", True)),
        notify=bool(general.get("notify", True)),
        targets=targets or default_targets(platform),
        source=source,
    )


def load_config(platform: str, path: Path | None = None) -> Config:
    found = find_config(path)
    if found is None:
        return parse_config(resources.read_text(resources.DEFAULT_CONFIG), platform)
    return parse_config(found.read_text(encoding="utf-8"), platform, source=found)


def save_setting(path: Path, section: str, key: str, value: Any) -> None:
    """Cambia un valor conservando comentarios y formato (lo usa la bandeja)."""
    import tomlkit

    document = tomlkit.parse(path.read_text(encoding="utf-8"))
    if section not in document:
        document[section] = tomlkit.table()
    document[section][key] = value
    path.write_text(tomlkit.dumps(document), encoding="utf-8")
