# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Claude Code en kitty, usando su control remoto.

Requiere en kitty.conf: `allow_remote_control socket-only` y `listen_on unix:@kitty`
(kitty exporta `KITTY_LISTEN_ON` a sus procesos). `paste-photo doctor` lo comprueba.
"""

from __future__ import annotations

import json
import logging
import subprocess
from collections.abc import Mapping
from typing import Any

from paste_photo.core.ports import WindowInfo
from paste_photo.targets._env_terminal import CTRL_V, EnvTerminalTarget, run
from paste_photo.targets._processes import ClaudeProcess
from paste_photo.targets.registry import TargetContext, register_target

log = logging.getLogger(__name__)


class KittyTarget(EnvTerminalTarget):
    name = "kitty"
    required_env = ("KITTY_WINDOW_ID", "KITTY_LISTEN_ON")

    def __init__(self, ctx: TargetContext) -> None:
        super().__init__(ctx)
        # (socket, ventana de kitty) → ventana del SO (`platform_window_id`: X11 y macOS)
        self._os_window: dict[tuple[str, str], int] = {}

    def describe(self, proc: ClaudeProcess) -> str:
        return f"kitty ventana {proc.environ['KITTY_WINDOW_ID']}"

    def send_ctrl_v(self, proc: ClaudeProcess) -> None:
        env = proc.environ
        run(["kitty", "@", "--to", env["KITTY_LISTEN_ON"], "send-text",
             "--match", f"id:{env['KITTY_WINDOW_ID']}", CTRL_V])

    def session_rank(self, procs: list[ClaudeProcess]) -> dict[int, tuple[int, ...]]:
        # Todas las ventanas del SO de kitty son del mismo proceso: empatan por ventana.
        # Primero la ventana de kitty con el foco, luego la activa de la pestaña activa de
        # cada ventana del SO.
        by_window: dict[tuple[str, str], tuple[int, ...]] = {}
        self._os_window = {}
        for listen in {p.environ["KITTY_LISTEN_ON"] for p in procs}:
            try:
                os_windows = json.loads(run(["kitty", "@", "--to", listen, "ls"]))
            except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as error:
                log.debug("kitty no dio sus ventanas: %s", error)
                continue
            for index, os_window in enumerate(os_windows):
                for tab in os_window.get("tabs", []):
                    for window in tab.get("windows", []):
                        shown = tab.get("is_active") and window.get("is_active")
                        key = (listen, str(window.get("id")))
                        by_window[key] = (
                            0 if window.get("is_focused") else 1, 0 if shown else 1, index)
                        if platform_id := os_window.get("platform_window_id"):
                            self._os_window[key] = int(platform_id)
        return {p.pid: by_window[key] for p in procs
                if (key := (p.environ["KITTY_LISTEN_ON"], p.environ["KITTY_WINDOW_ID"]))
                in by_window}

    def window_of(self, proc: ClaudeProcess, windows: list[WindowInfo]) -> WindowInfo | None:
        wanted = self._os_window.get((proc.environ["KITTY_LISTEN_ON"],
                                      proc.environ["KITTY_WINDOW_ID"]))
        exact = next((w for w in windows if w.id == wanted), None)
        return exact or super().window_of(proc, windows)


@register_target("kitty", platforms=("linux", "macos"))
def build(options: Mapping[str, Any], ctx: TargetContext) -> KittyTarget:
    return KittyTarget(ctx)
