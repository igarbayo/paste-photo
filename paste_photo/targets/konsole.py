# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Claude Code en Konsole (KDE), por su interfaz D-Bus (X11 y Wayland)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from paste_photo.targets._env_terminal import CTRL_V, EnvTerminalTarget
from paste_photo.targets._processes import ClaudeProcess
from paste_photo.targets.registry import TargetContext, register_target

SESSION_INTERFACE = "org.kde.konsole.Session"


class KonsoleTarget(EnvTerminalTarget):
    name = "konsole"
    required_env = ("KONSOLE_DBUS_SERVICE", "KONSOLE_DBUS_SESSION")

    def describe(self, proc: ClaudeProcess) -> str:
        return f"Konsole {proc.environ['KONSOLE_DBUS_SESSION']}"

    def send_ctrl_v(self, proc: ClaudeProcess) -> None:
        from jeepney import DBusAddress, new_method_call
        from jeepney.io.blocking import open_dbus_connection

        address = DBusAddress(proc.environ["KONSOLE_DBUS_SESSION"],
                              bus_name=proc.environ["KONSOLE_DBUS_SERVICE"],
                              interface=SESSION_INTERFACE)
        with open_dbus_connection(bus="SESSION") as conn:
            reply = conn.send_and_get_reply(new_method_call(address, "sendText", "s", (CTRL_V,)),
                                            timeout=5)
        if reply.header.message_type.name == "error":
            raise RuntimeError(f"Konsole rechazó sendText: {reply.body}")


@register_target("konsole", platforms=("linux",))
def build(options: Mapping[str, Any], ctx: TargetContext) -> KonsoleTarget:
    return KonsoleTarget(ctx)
