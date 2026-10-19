"""Registro de destinos (plugin registry).

Añadir un destino = crear un módulo en `paste_photo/targets/`, decorar su
constructor con `@register_target("nombre")` y listarlo en `_BUILTIN_MODULES`.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from paste_photo.core.ports import FocusManager, Keyboard, TargetStrategy
from paste_photo.core.recency import Recency


@dataclass(frozen=True)
class TargetContext:
    """Servicios de plataforma que un destino puede necesitar."""

    platform: str
    focus: FocusManager
    keyboard: Keyboard
    recency: Recency = field(default_factory=Recency)


TargetBuilder = Callable[[Mapping[str, Any], TargetContext], TargetStrategy]

_REGISTRY: dict[str, TargetBuilder] = {}
_BUILTIN_MODULES = ("windows_terminal", "desktop_app", "browser", "vscode")
_loaded = False


def register_target(name: str) -> Callable[[TargetBuilder], TargetBuilder]:
    def decorator(builder: TargetBuilder) -> TargetBuilder:
        if name in _REGISTRY:
            raise ValueError(f"Destino duplicado: {name}")
        _REGISTRY[name] = builder
        return builder

    return decorator


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
    return _REGISTRY[kind](options, ctx)
