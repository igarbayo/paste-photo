# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Detección de la sesión gráfica de Linux: decide qué backend de ventanas/teclado usar."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

BACKENDS = ("x11", "gnome", "kde", "none")
OVERRIDE_ENV = "PASTE_PHOTO_BACKEND"  # forzar backend (pruebas o casos raros)


@dataclass(frozen=True)
class Session:
    wayland: bool
    desktop: str  # "gnome" | "kde" | "other"
    backend: str  # uno de BACKENDS

    def describe(self) -> str:
        kind = "Wayland" if self.wayland else "X11"
        return f"{kind}, escritorio {self.desktop}, backend {self.backend}"


def detect(env: Mapping[str, str] | None = None) -> Session:
    env = os.environ if env is None else env
    desktop_raw = ":".join((env.get("XDG_CURRENT_DESKTOP", ""),
                            env.get("DESKTOP_SESSION", ""))).lower()
    if "gnome" in desktop_raw or "ubuntu" in desktop_raw or "unity" in desktop_raw:
        desktop = "gnome"
    elif "kde" in desktop_raw or "plasma" in desktop_raw:
        desktop = "kde"
    else:
        desktop = "other"
    wayland = env.get("XDG_SESSION_TYPE") == "wayland" or (
        bool(env.get("WAYLAND_DISPLAY")) and env.get("XDG_SESSION_TYPE") != "x11"
    )

    forced = env.get(OVERRIDE_ENV, "").lower()
    if forced in BACKENDS:
        return Session(wayland, desktop, forced)
    if not wayland:
        backend = "x11" if env.get("DISPLAY") else "none"
    elif desktop in ("gnome", "kde"):
        backend = desktop
    else:
        # Otro compositor Wayland (wlroots, WSLg...): las apps X11 (XWayland) sí se ven.
        backend = "x11" if env.get("DISPLAY") else "none"
    return Session(wayland, desktop, backend)
