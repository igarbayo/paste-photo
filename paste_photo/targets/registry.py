# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Registro de destinos (plugin registry).

Añadir un destino = crear un módulo en `paste_photo/targets/`, decorar su
constructor con `@register_target("nombre")` y listarlo en `_BUILTIN_MODULES`.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from paste_photo.core.ports import FocusManager, Keyboard, TargetStrategy, WindowSystem
from paste_photo.core.recency import Recency


@dataclass(frozen=True)
class TargetContext:
    """Servicios de plataforma que un destino puede necesitar."""

    platform: str
    focus: FocusManager
    keyboard: Keyboard
    recency: Recency = field(default_factory=Recency)
    # Sistema de ventanas (Linux: X11, GNOME Shell, KWin). None si la sesión no lo permite
    # o si el SO lo resuelve de otra forma (Windows usa UI Automation directamente).
    windows: WindowSystem | None = None


TargetBuilder = Callable[[Mapping[str, Any], TargetContext], TargetStrategy]


@dataclass(frozen=True)
class TargetEntry:
    builder: TargetBuilder
    platforms: frozenset[str] | None  # None = cualquier SO


_REGISTRY: dict[str, TargetEntry] = {}
_BUILTIN_MODULES = (
    "browser_extension",
    "windows_terminal",
    "browser",
    "tmux",
    "kitty",
    "wezterm",
    "konsole",
    "orca",
    "linux_terminal",
    "desktop_app",
    "vscode",
)
_loaded = False


def register_target(
    name: str, *, platforms: tuple[str, ...] | None = None
) -> Callable[[TargetBuilder], TargetBuilder]:
    """Registra un destino. `platforms`: SO donde funciona ("windows", "linux", "macos")."""

    def decorator(builder: TargetBuilder) -> TargetBuilder:
        if name in _REGISTRY:
            raise ValueError(f"Destino duplicado: {name}")
        _REGISTRY[name] = TargetEntry(builder, frozenset(platforms) if platforms else None)
        return builder

    return decorator


def supports(kind: str, platform: str) -> bool:
    """¿El destino `kind` funciona en este SO? (los de otros SO se omiten sin error)."""
    _load_builtins()
    entry = _REGISTRY.get(kind)
    return entry is not None and (entry.platforms is None or platform in entry.platforms)


def _load_builtins() -> None:
    global _loaded
    if _loaded:
        return
    for module in _BUILTIN_MODULES:
        importlib.import_module(f"paste_photo.targets.{module}")
    _loaded = True


def available_targets() -> list[str]:
    _load_builtins()
    return sorted(_REGISTRY)


def build_target(options: Mapping[str, Any], ctx: TargetContext) -> TargetStrategy:
    _load_builtins()
    kind = options.get("type")
    if kind not in _REGISTRY:
        raise ValueError(f"Destino desconocido {kind!r}. Disponibles: {available_targets()}")
    entry = _REGISTRY[kind]
    if entry.platforms is not None and ctx.platform not in entry.platforms:
        raise ValueError(f"El destino {kind} no funciona en {ctx.platform}")
    return entry.builder(options, ctx)
