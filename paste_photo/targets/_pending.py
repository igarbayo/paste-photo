# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Utilidad para registrar destinos todavía no implementados."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from paste_photo.targets.registry import TargetContext, register_target


def register_pending(name: str, hint: str) -> None:
    """Registra `name` para que aparezca en la lista, pero falle con un mensaje claro."""

    @register_target(name)
    def build(options: Mapping[str, Any], ctx: TargetContext):
        raise NotImplementedError(
            f"El destino {name!r} aún no está implementado. {hint} "
            "Receta en paste_photo/targets/CLAUDE.md."
        )
