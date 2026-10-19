# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Base para terminales/multiplexores con IPC (tmux, kitty, WezTerm, Konsole).

El proceso `claude` hereda variables de entorno que identifican su panel exacto
(`TMUX_PANE`, `KITTY_WINDOW_ID`, `WEZTERM_PANE`, `KONSOLE_DBUS_SESSION`...). Con ellas se
escribe Ctrl+V (`\\x16`) directamente en ese panel: no hace falta foco, ni ventana activa,
ni simular teclas, así que funciona igual en X11 y en Wayland y aunque la pestaña no sea
la visible. Claude Code lee entonces la imagen del portapapeles (`xclip`/`wl-paste`).
"""

from __future__ import annotations

import logging
import subprocess
from collections.abc import Mapping, Sequence

from paste_photo.core.events import ScreenshotCaptured
from paste_photo.core.ports import TargetHandle
from paste_photo.targets._processes import ClaudeProcess, claude_processes, owning_window
from paste_photo.targets.registry import TargetContext

log = logging.getLogger(__name__)

CTRL_V = "\x16"
COMMAND_TIMEOUT_S = 5


# Variables que delatan un multiplexor *dentro* del terminal: si están, el panel exacto lo
# conoce el multiplexor y no el terminal exterior (que mandaría Ctrl+V al panel activo).
INNER_MULTIPLEXER_ENV = ("TMUX",)
# Todo lo que cubre algún destino IPC (lo usa `linux_terminal` para no duplicar).
IPC_ENV_MARKERS = (("TMUX", "TMUX_PANE"), ("KITTY_WINDOW_ID", "KITTY_LISTEN_ON"),
                   ("WEZTERM_PANE",), ("KONSOLE_DBUS_SERVICE", "KONSOLE_DBUS_SESSION"))


def handled_by_ipc(environ: Mapping[str, str]) -> bool:
    return any(all(environ.get(var) for var in marker) for marker in IPC_ENV_MARKERS)


class EnvTerminalTarget:
    name = "env_terminal"
    required_env: tuple[str, ...] = ()
    excluded_env: tuple[str, ...] = INNER_MULTIPLEXER_ENV

    def __init__(self, ctx: TargetContext) -> None:
        self._ctx = ctx

    # --- a implementar por cada terminal -----------------------------------

    def describe(self, proc: ClaudeProcess) -> str:
        raise NotImplementedError

    def send_ctrl_v(self, proc: ClaudeProcess) -> None:
        raise NotImplementedError

    # --- TargetStrategy ----------------------------------------------------

    def matches(self, proc: ClaudeProcess) -> bool:
        return all(proc.environ.get(var) for var in self.required_env) and not any(
            proc.environ.get(var) for var in self.excluded_env
        )

    def locate(self) -> TargetHandle | None:
        procs = [p for p in claude_processes() if self.matches(p)]
        if not procs:
            return None
        windows = self._list_windows()
        handles = []
        for proc in procs:
            window = owning_window(proc.ancestors, windows) if windows else None
            label = self.describe(proc) + (f" · {window.title}" if window else "")
            handles.append(TargetHandle(window_id=window.id if window else 0, label=label,
                                        extra={"proc": proc}))
        # El orquestador ordena destinos entre sí; aquí, el de la ventana más reciente.
        handles.sort(key=lambda h: self._ctx.recency.last_seen(h.window_id), reverse=True)
        best = handles[0]
        return TargetHandle(best.window_id, best.label, {**best.extra, "candidates": handles})

    def paste(self, handle: TargetHandle, shot: ScreenshotCaptured | None = None) -> None:
        errors = []
        for candidate in handle.extra.get("candidates", [handle]):
            try:
                self.send_ctrl_v(candidate.extra["proc"])
                return
            except (OSError, subprocess.SubprocessError, RuntimeError) as error:
                log.info("%s: no se pudo pegar en %r: %s", self.name, candidate.label, error)
                errors.append(str(error))
        raise RuntimeError(f"{self.name}: " + "; ".join(errors))

    # --- helpers -----------------------------------------------------------

    def _list_windows(self):
        if self._ctx.windows is None:
            return []
        try:
            return self._ctx.windows.list_windows()
        except Exception:
            log.debug("No se pudieron listar ventanas", exc_info=True)
            return []


def run(cmd: Sequence[str], env: Mapping[str, str] | None = None) -> str:
    result = subprocess.run(list(cmd), capture_output=True, text=True, timeout=COMMAND_TIMEOUT_S,
                            env=dict(env) if env is not None else None)
    if result.returncode != 0:
        raise RuntimeError(f"{cmd[0]} falló ({result.returncode}): {result.stderr.strip()}")
    return result.stdout
