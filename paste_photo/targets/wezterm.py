# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Claude Code en WezTerm, usando `wezterm cli` (sin configuración extra)."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from paste_photo.targets._env_terminal import CTRL_V, EnvTerminalTarget, run
from paste_photo.targets._processes import ClaudeProcess
from paste_photo.targets.registry import TargetContext, register_target


class WezTermTarget(EnvTerminalTarget):
    name = "wezterm"
    required_env = ("WEZTERM_PANE",)

    def describe(self, proc: ClaudeProcess) -> str:
        return f"WezTerm panel {proc.environ['WEZTERM_PANE']}"

    def send_ctrl_v(self, proc: ClaudeProcess) -> None:
        env = dict(os.environ)
        if socket := proc.environ.get("WEZTERM_UNIX_SOCKET"):
            env["WEZTERM_UNIX_SOCKET"] = socket  # la instancia de WezTerm de ese panel
        run(["wezterm", "cli", "send-text", "--no-paste",
             "--pane-id", proc.environ["WEZTERM_PANE"], CTRL_V], env=env)


@register_target("wezterm", platforms=("linux", "macos"))
def build(options: Mapping[str, Any], ctx: TargetContext) -> WezTermTarget:
    return WezTermTarget(ctx)
