# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Claude Code dentro de tmux (en cualquier terminal, X11 o Wayland)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from paste_photo.targets._env_terminal import EnvTerminalTarget, run
from paste_photo.targets._processes import ClaudeProcess
from paste_photo.targets.registry import TargetContext, register_target


def tmux_socket(tmux_env: str) -> str:
    """`TMUX=/tmp/tmux-1000/default,1234,0` → ruta del socket del servidor."""
    return tmux_env.split(",", 1)[0]


class TmuxTarget(EnvTerminalTarget):
    name = "tmux"
    required_env = ("TMUX", "TMUX_PANE")
    excluded_env = ()  # tmux es la capa más interna

    def describe(self, proc: ClaudeProcess) -> str:
        return f"tmux {proc.environ['TMUX_PANE']}"

    def send_ctrl_v(self, proc: ClaudeProcess) -> None:
        socket = tmux_socket(proc.environ["TMUX"])
        run(["tmux", "-S", socket, "send-keys", "-t", proc.environ["TMUX_PANE"], "C-v"])


@register_target("tmux", platforms=("linux", "macos"))
def build(options: Mapping[str, Any], ctx: TargetContext) -> TmuxTarget:
    return TmuxTarget(ctx)
