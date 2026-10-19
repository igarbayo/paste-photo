# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Claude Code en kitty, usando su control remoto.

Requiere en kitty.conf: `allow_remote_control socket-only` y `listen_on unix:@kitty`
(kitty exporta `KITTY_LISTEN_ON` a sus procesos). `paste-photo doctor` lo comprueba.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from paste_photo.targets._env_terminal import CTRL_V, EnvTerminalTarget, run
from paste_photo.targets._processes import ClaudeProcess
from paste_photo.targets.registry import TargetContext, register_target


class KittyTarget(EnvTerminalTarget):
    name = "kitty"
    required_env = ("KITTY_WINDOW_ID", "KITTY_LISTEN_ON")

    def describe(self, proc: ClaudeProcess) -> str:
        return f"kitty ventana {proc.environ['KITTY_WINDOW_ID']}"

    def send_ctrl_v(self, proc: ClaudeProcess) -> None:
        env = proc.environ
        run(["kitty", "@", "--to", env["KITTY_LISTEN_ON"], "send-text",
             "--match", f"id:{env['KITTY_WINDOW_ID']}", CTRL_V])


@register_target("kitty", platforms=("linux", "macos"))
def build(options: Mapping[str, Any], ctx: TargetContext) -> KittyTarget:
    return KittyTarget(ctx)
