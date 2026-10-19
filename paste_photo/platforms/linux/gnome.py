# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""GNOME Wayland: ventanas y teclado a través de la extensión de GNOME Shell de paste-photo.

En Wayland una app no puede ver otras ventanas ni simular teclas; GNOME Shell sí. La
extensión (`gnome_extension/`) publica en el bus de sesión:
    io.github.igarbayo.PastePhoto  /io/github/igarbayo/PastePhoto
    ListWindows() -> s (JSON)   ActiveWindow() -> t   Activate(t)   SendKeys(s)
Se instala con `paste-photo setup gnome` (requiere cerrar y abrir sesión una vez).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from paste_photo import resources
from paste_photo.core.ports import WindowInfo

BUS_NAME = "io.github.igarbayo.PastePhoto"
OBJECT_PATH = "/io/github/igarbayo/PastePhoto"
INTERFACE = "io.github.igarbayo.PastePhoto"
EXTENSION_UUID = "paste-photo@igarbayo.github.io"


def _call(method: str, signature: str = "", args: tuple = ()):
    from jeepney import DBusAddress, new_method_call
    from jeepney.io.blocking import open_dbus_connection

    address = DBusAddress(OBJECT_PATH, bus_name=BUS_NAME, interface=INTERFACE)
    with open_dbus_connection(bus="SESSION") as conn:
        reply = conn.send_and_get_reply(new_method_call(address, method, signature, args),
                                        timeout=3)
    if reply.header.message_type.name == "error":
        raise RuntimeError(f"Extensión de GNOME: {method} falló: {reply.body}")
    return reply.body


def extension_available() -> bool:
    try:
        _call("ActiveWindow")
        return True
    except Exception:
        return False


def parse_windows(payload: str) -> list[WindowInfo]:
    return [WindowInfo(int(w["id"]), w.get("title") or "", int(w.get("pid") or 0),
                       w.get("app_id") or "") for w in json.loads(payload)]


class GnomeShellWindowSystem:
    def list_windows(self) -> list[WindowInfo]:
        return parse_windows(_call("ListWindows")[0])

    def active_window(self) -> int | None:
        window_id = int(_call("ActiveWindow")[0])
        return window_id or None

    def activate(self, window_id: int) -> None:
        _call("Activate", "t", (window_id,))


class GnomeShellKeyboard:
    """La extensión solo acepta combinaciones de pegado (ctrl+v, alt+v, ctrl+shift+v)."""

    def send_hotkey(self, hotkey: str) -> None:
        _call("SendKeys", "s", (hotkey,))


def install_extension(home: Path | None = None) -> str:
    """Copia la extensión y la marca como activada (efectiva al volver a iniciar sesión)."""
    base = (home or Path.home()) / ".local" / "share" / "gnome-shell" / "extensions"
    target = base / EXTENSION_UUID
    shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(resources.path("gnome_extension"), target)
    enabled = _enable_with_gsettings()
    lines = [f"Extensión copiada en {target}"]
    if enabled:
        lines.append("Activada en la configuración de GNOME Shell.")
    else:
        lines.append(f"Actívala con: gnome-extensions enable {EXTENSION_UUID}")
    lines.append("Cierra sesión y vuelve a entrar para que GNOME la cargue (Wayland no puede")
    lines.append("recargar GNOME Shell en caliente). Después: paste-photo doctor")
    return "\n".join(lines)


def _enable_with_gsettings() -> bool:
    if shutil.which("gsettings") is None:
        return False
    try:
        out = subprocess.run(["gsettings", "get", "org.gnome.shell", "enabled-extensions"],
                             capture_output=True, text=True, timeout=5).stdout.strip()
        current = [] if out in ("@as []", "") else json.loads(out.replace("'", '"'))
        if EXTENSION_UUID not in current:
            current.append(EXTENSION_UUID)
            value = "[" + ", ".join(f"'{uuid}'" for uuid in current) + "]"
            subprocess.run(["gsettings", "set", "org.gnome.shell", "enabled-extensions", value],
                           check=True, timeout=5)
        return True
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
