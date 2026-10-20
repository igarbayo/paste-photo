# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Claude Code en Terminal.app (macOS): AppleScript selecciona la pestaña → foco → Ctrl+V.

Terminal no tiene forma de escribir en una pestaña sin teclear (`do script` añade Enter), así
que se trae al frente la pestaña cuyo `tty` es el del proceso `claude`, se pulsa Ctrl+V (la
tecla de pegado de imágenes de Claude Code en macOS) y se vuelve a la pestaña que estaba
seleccionada. El foco de ventana lo restaura el Orchestrator.

Con las pestañas nativas de macOS (las de Terminal actual), AppleScript presenta cada pestaña
como una ventana con una sola pestaña: para volver a la tuya se guarda la ventana delantera de
Terminal antes de seleccionar la de Claude y después se vuelve a poner delante.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Mapping
from typing import Any

import psutil

from paste_photo.core.ports import WindowInfo
from paste_photo.targets._applescript import osascript, parse_rows
from paste_photo.targets._env_terminal import EnvTerminalTarget
from paste_photo.targets._processes import ClaudeProcess, process_name
from paste_photo.targets.registry import TargetContext, register_target

log = logging.getLogger(__name__)

APP_PROCESS = "terminal"
DEFAULT_PASTE_KEYS = "ctrl+v"
SELECT_SCRIPT = """
on run argv
    set wanted to item 1 of argv
    -- dentro del tell, `tab` es la clase "pestaña" de Terminal, no el tabulador
    set sep to character id 9
    tell application id "com.apple.Terminal"
        -- con pestañas nativas, la ventana delantera es la pestaña visible que usabas
        set frontId to 0
        if (count of windows) > 0 then set frontId to id of front window
        repeat with w in windows
            set previous to 0
            set found to 0
            set i to 0
            repeat with t in tabs of w
                set i to i + 1
                if selected of t then set previous to i
                if tty of t is wanted then set found to i
            end repeat
            if found > 0 then
                set selected of tab found of w to true
                set index of w to 1
                activate
                return (id of w as text) & sep & previous & sep & found & sep & frontId
            end if
        end repeat
    end tell
    error "pestaña de Terminal no encontrada: " & wanted
end run
"""
RESTORE_SCRIPT = """
on run argv
    set wid to (item 1 of argv) as integer
    set ti to (item 2 of argv) as integer
    set frontId to (item 3 of argv) as integer
    tell application id "com.apple.Terminal"
        -- pestañas clásicas: varias pestañas dentro de una ventana
        if ti > 0 then set selected of tab ti of window id wid to true
        -- pestañas nativas: cada pestaña es una ventana del grupo
        if frontId > 0 then set index of window id frontId to 1
    end tell
end run
"""


def tty_of(pid: int) -> str:
    try:
        tty = psutil.Process(pid).terminal()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        tty = None
    if not tty:
        raise RuntimeError(f"no se conoce el tty del proceso {pid}")
    return tty


class TerminalAppTarget(EnvTerminalTarget):
    name = "terminal_app"

    def __init__(self, ctx: TargetContext, *, paste_keys: str = DEFAULT_PASTE_KEYS,
                 settle_ms: int = 200, restore_tab: bool = True) -> None:
        super().__init__(ctx)
        self._paste_keys = paste_keys
        self._settle_s = settle_ms / 1000
        self._restore_tab = restore_tab

    def matches(self, proc: ClaudeProcess) -> bool:
        return super().matches(proc) and proc.environ.get("TERM_PROGRAM") == "Apple_Terminal"

    def describe(self, proc: ClaudeProcess) -> str:
        try:
            return f"Terminal {tty_of(proc.pid).removeprefix('/dev/')}"
        except RuntimeError:
            return f"Terminal (pid {proc.pid})"

    def send_ctrl_v(self, proc: ClaudeProcess) -> None:
        rows = parse_rows(osascript(SELECT_SCRIPT, tty_of(proc.pid)), 4)
        if not rows:
            raise RuntimeError("Terminal no devolvió la pestaña")
        window, previous, found, front = rows[0]
        time.sleep(self._settle_s)
        self._ctx.keyboard.send_hotkey(self._paste_keys)
        time.sleep(self._settle_s)
        tab = previous if previous not in ("0", found) else "0"
        front = front if front != window else "0"
        if self._restore_tab and (tab, front) != ("0", "0"):
            try:
                osascript(RESTORE_SCRIPT, window, tab, front)
            except (OSError, RuntimeError) as error:
                log.debug("No se pudo volver a la pestaña anterior: %s", error)

    def window_of(self, proc: ClaudeProcess, windows: list[WindowInfo]) -> WindowInfo | None:
        # Todas las ventanas son del mismo proceso: la usada más recientemente.
        return max(windows, key=lambda w: self._ctx.recency.last_seen(w.id), default=None)

    def _list_windows(self) -> list[WindowInfo]:
        return [w for w in super()._list_windows() if process_name(w.pid) == APP_PROCESS]


@register_target("terminal_app", platforms=("macos",))
def build(options: Mapping[str, Any], ctx: TargetContext) -> TerminalAppTarget:
    return TerminalAppTarget(
        ctx,
        paste_keys=options.get("paste_keys", DEFAULT_PASTE_KEYS),
        settle_ms=int(options.get("settle_ms", 200)),
        restore_tab=bool(options.get("restore_tab", True)),
    )
