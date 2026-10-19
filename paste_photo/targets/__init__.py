# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Destinos donde puede estar Claude Code. Cada módulo se registra con `@register_target`."""

from paste_photo.targets.registry import (
    TargetContext,
    available_targets,
    build_target,
    register_target,
)

__all__ = ["TargetContext", "available_targets", "build_target", "register_target"]
