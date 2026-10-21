# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Claude Code en WezTerm, usando `wezterm cli` (sin configuración extra)."""

from __future__ import annotations

import json
import logging
import os
import subprocess
from collections.abc import Mapping
from typing import Any

from paste_photo.targets._env_terminal import CTRL_V, EnvTerminalTarget, run
from paste_photo.targets._processes import ClaudeProcess
from paste_photo.targets.registry import TargetContext, register_target

log = logging.getLogger(__name__)


def cli_env(proc: ClaudeProcess) -> dict[str, str]:
    env = dict(os.environ)
    if socket := proc.environ.get("WEZTERM_UNIX_SOCKET"):
        env["WEZTERM_UNIX_SOCKET"] = socket  # la instancia de WezTerm de ese panel
    return env


class WezTermTarget(EnvTerminalTarget):
    name = "wezterm"
    required_env = ("WEZTERM_PANE",)

    def describe(self, proc: ClaudeProcess) -> str:
        return f"WezTerm panel {proc.environ['WEZTERM_PANE']}"

    def send_ctrl_v(self, proc: ClaudeProcess) -> None:
        run(["wezterm", "cli", "send-text", "--no-paste",
             "--pane-id", proc.environ["WEZTERM_PANE"], CTRL_V], env=cli_env(proc))

    def session_rank(self, procs: list[ClaudeProcess]) -> dict[int, tuple[int, ...]]:
        # Todas las ventanas de WezTerm son del mismo proceso: empatan por ventana. Primero
        # el panel con el foco de algún cliente (GUI), luego el activo de cada pestaña.
        by_pane: dict[tuple[str, str], tuple[int, ...]] = {}
        groups: dict[str, ClaudeProcess] = {}
        for proc in procs:
            groups.setdefault(proc.environ.get("WEZTERM_UNIX_SOCKET", ""), proc)
        for socket, proc in groups.items():
            env = cli_env(proc)
            try:
                panes = json.loads(run(["wezterm", "cli", "list", "--format", "json"], env=env))
            except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as error:
                log.debug("WezTerm no dio sus paneles: %s", error)
                continue
            try:
                clients = json.loads(run(["wezterm", "cli", "list-clients", "--format", "json"],
                                         env=env))
            except (OSError, RuntimeError, subprocess.SubprocessError, ValueError):
                clients = []
            focused = {str(c.get("focused_pane_id")) for c in clients}
            for pane in panes:
                pane_id = str(pane.get("pane_id"))
                by_pane[(socket, pane_id)] = (0 if pane_id in focused else 1,
                                              0 if pane.get("is_active") else 1)
        return {p.pid: by_pane[key] for p in procs
                if (key := (p.environ.get("WEZTERM_UNIX_SOCKET", ""), p.environ["WEZTERM_PANE"]))
                in by_pane}


@register_target("wezterm", platforms=("linux", "macos"))
def build(options: Mapping[str, Any], ctx: TargetContext) -> WezTermTarget:
    return WezTermTarget(ctx)
