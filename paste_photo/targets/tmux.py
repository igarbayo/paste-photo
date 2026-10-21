# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Claude Code dentro de tmux (en cualquier terminal, X11 o Wayland)."""

from __future__ import annotations

import logging
import subprocess
from collections.abc import Mapping
from typing import Any

import psutil

from paste_photo.core.ports import WindowInfo
from paste_photo.targets._applescript import parse_rows
from paste_photo.targets._env_terminal import EnvTerminalTarget, run
from paste_photo.targets._processes import ClaudeProcess, owner_windows, process_name
from paste_photo.targets.registry import TargetContext, register_target

log = logging.getLogger(__name__)

# Panel a la vista: sesión con algún cliente, ventana activa de la sesión y panel activo.
PANES_FORMAT = "#{pane_id}\t#{session_name}\t#{session_attached}\t#{window_active}" \
               "\t#{pane_active}"
# Última tecla de cada cliente (epoch): la sesión del terminal que usaste por última vez. El
# PID del cliente lleva a la ventana del terminal donde está conectado.
CLIENTS_FORMAT = "#{client_session}\t#{client_activity}\t#{client_pid}"
# Terminales de macOS cuyas sesiones no cuelgan de su ventana (iTerm2: de iTermServer): la
# ventana del cliente es la de esa app usada más recientemente.
APP_OF_TERM_PROGRAM = {"iTerm.app": "iterm2", "Apple_Terminal": "terminal"}


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

    def __init__(self, ctx: TargetContext) -> None:
        super().__init__(ctx)
        self._clients: dict[tuple[str, str], list[int]] = {}  # (socket, panel) → PIDs

    def describe(self, proc: ClaudeProcess) -> str:
        return f"tmux {proc.environ['TMUX_PANE']}"

    def send_ctrl_v(self, proc: ClaudeProcess) -> None:
        socket = tmux_socket(proc.environ["TMUX"])
        run(["tmux", "-S", socket, "send-keys", "-t", proc.environ["TMUX_PANE"], "C-v"])

    def session_rank(self, procs: list[ClaudeProcess]) -> dict[int, tuple[int, ...]]:
        # Los paneles cuelgan del servidor de tmux, no de la ventana del terminal: todos
        # empatan en la recencia por ventana.
        by_pane: dict[tuple[str, str], tuple[int, ...]] = {}
        self._clients = {}
        for socket in {tmux_socket(p.environ["TMUX"]) for p in procs}:
            try:
                panes = run(["tmux", "-S", socket, "list-panes", "-a", "-F", PANES_FORMAT])
                clients = run(["tmux", "-S", socket, "list-clients", "-F", CLIENTS_FORMAT])
            except (OSError, RuntimeError, subprocess.SubprocessError) as error:
                log.debug("tmux no dio sus paneles: %s", error)
                continue
            activity: dict[str, int] = {}
            pids: dict[str, list[tuple[int, int]]] = {}
            for session, at, pid in parse_rows(clients, 3):
                activity[session] = max(activity.get(session, 0), _int(at))
                pids.setdefault(session, []).append((_int(at), _int(pid)))
            for pane, session, attached, window_active, pane_active in parse_rows(panes, 5):
                shown = attached != "0" and window_active == "1" and pane_active == "1"
                by_pane[(socket, pane)] = (0 if shown else 1, -activity.get(session, 0))
                # Clientes de su sesión, el de la última tecla primero.
                self._clients[(socket, pane)] = [pid for _, pid in
                                                 sorted(pids.get(session, []), reverse=True)]
        return {p.pid: by_pane[key] for p in procs
                if (key := (tmux_socket(p.environ["TMUX"]), p.environ["TMUX_PANE"])) in by_pane}

    def window_of(self, proc: ClaudeProcess, windows: list[WindowInfo]) -> WindowInfo | None:
        # El panel cuelga del servidor de tmux (sin ventana): la del terminal del cliente
        # conectado a su sesión. Sin ella, tmux nunca ganaba a otro Claude que estuvieras usando.
        key = (tmux_socket(proc.environ["TMUX"]), proc.environ["TMUX_PANE"])
        for pid in self._clients.get(key, []):
            try:
                client = psutil.Process(pid)
                ancestors = [p.pid for p in client.parents()]
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            if window := self.most_recent(owner_windows(ancestors, windows)):
                return window
            try:
                app = APP_OF_TERM_PROGRAM.get(client.environ().get("TERM_PROGRAM", ""))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                app = None
            if app and (window := self.most_recent(
                    [w for w in windows if process_name(w.pid) == app])):
                return window
        return None


@register_target("tmux", platforms=("linux", "macos"))
def build(options: Mapping[str, Any], ctx: TargetContext) -> TmuxTarget:
    return TmuxTarget(ctx)
