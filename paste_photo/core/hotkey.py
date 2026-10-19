# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Parseo de combinaciones de teclas en texto ("alt+v", "ctrl+shift+v")."""

from __future__ import annotations

from dataclasses import dataclass

MODIFIERS = ("ctrl", "alt", "shift", "win", "cmd")
_ALIASES = {"control": "ctrl", "option": "alt", "super": "win", "meta": "win", "command": "cmd"}


@dataclass(frozen=True)
class Hotkey:
    modifiers: tuple[str, ...]
    key: str


def parse_hotkey(text: str) -> Hotkey:
    parts = [p.strip().lower() for p in text.split("+") if p.strip()]
    if not parts:
        raise ValueError(f"Combinación de teclas vacía: {text!r}")
    parts = [_ALIASES.get(p, p) for p in parts]
    *mods, key = parts
    unknown = [m for m in mods if m not in MODIFIERS]
    if unknown:
        raise ValueError(f"Modificador desconocido {unknown} en {text!r}")
    if key in MODIFIERS:
        raise ValueError(f"Falta la tecla principal en {text!r}")
    # Orden canónico para que "v+alt" no exista y "shift+ctrl" == "ctrl+shift".
    ordered = tuple(m for m in MODIFIERS if m in mods)
    return Hotkey(modifiers=ordered, key=key)
