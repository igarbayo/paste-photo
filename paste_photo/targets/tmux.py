# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Claude Code dentro de tmux (en cualquier terminal, X11 o Wayland)."""

from __future__ import annotations

import logging
import subprocess
from collections.abc import Mapping
from typing import Any

from paste_photo.targets._applescript import parse_rows
from paste_photo.targets._env_terminal import EnvTerminalTarget, run
from paste_photo.targets._processes import ClaudeProcess
from paste_photo.targets.registry import TargetContext, register_target

log = logging.getLogger(__name__)

# Panel a la vista: sesión con algún cliente, ventana activa de la sesión y panel activo.
PANES_FORMAT = "#{pane_id}\t#{session_name}\t#{session_attached}\t#{window_active}" \
               "\t#{pane_active}"
# Última tecla de cada cliente (epoch): la sesión del terminal que usaste por última vez.
CLIENTS_FORMAT = "#{client_session}\t#{client_activity}"


def _int(text: str) -> int:
    try:
        return int(text)
    except ValueError:
        return 0


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

    def session_rank(self, procs: list[ClaudeProcess]) -> dict[int, tuple[int, ...]]:
        # Los paneles cuelgan del servidor de tmux, no de la ventana del terminal: todos
        # empatan en la recencia por ventana.
        by_pane: dict[tuple[str, str], tuple[int, ...]] = {}
        for socket in {tmux_socket(p.environ["TMUX"]) for p in procs}:
            try:
                panes = run(["tmux", "-S", socket, "list-panes", "-a", "-F", PANES_FORMAT])
                clients = run(["tmux", "-S", socket, "list-clients", "-F", CLIENTS_FORMAT])
            except (OSError, RuntimeError, subprocess.SubprocessError) as error:
                log.debug("tmux no dio sus paneles: %s", error)
                continue
            activity: dict[str, int] = {}
            for session, at in parse_rows(clients, 2):
                activity[session] = max(activity.get(session, 0), _int(at))
            for pane, session, attached, window_active, pane_active in parse_rows(panes, 5):
                shown = attached != "0" and window_active == "1" and pane_active == "1"
                by_pane[(socket, pane)] = (0 if shown else 1, -activity.get(session, 0))
        return {p.pid: by_pane[key] for p in procs
                if (key := (tmux_socket(p.environ["TMUX"]), p.environ["TMUX_PANE"])) in by_pane}


@register_target("tmux", platforms=("linux", "macos"))
def build(options: Mapping[str, Any], ctx: TargetContext) -> TmuxTarget:
    return TmuxTarget(ctx)
