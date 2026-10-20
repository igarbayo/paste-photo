# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Claude Code en iTerm2 (macOS), por AppleScript: sin foco y en cualquier pestaña.

iTerm2 exporta `ITERM_SESSION_ID=w0t1p0:<UUID>`; el UUID es el `unique id` de la sesión en
AppleScript. `write text ... without newline` escribe Ctrl+V (`\\x16`) en esa sesión como si
se tecleara, sin traerla al frente; Claude Code inserta `[Image #N]` en su cursor.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from paste_photo.core.ports import WindowInfo
from paste_photo.targets._applescript import osascript
from paste_photo.targets._env_terminal import CTRL_V, EnvTerminalTarget
from paste_photo.targets._processes import ClaudeProcess, process_name
from paste_photo.targets.registry import TargetContext, register_target

APP_PROCESS = "iterm2"
WRITE_SCRIPT = """
on run argv
    set wanted to item 1 of argv
    set payload to item 2 of argv
    tell application id "com.googlecode.iterm2"
        repeat with w in windows
            repeat with t in tabs of w
                repeat with s in sessions of t
                    if unique id of s is wanted then
                        tell s to write text payload without newline
                        return "ok"
                    end if
                end repeat
            end repeat
        end repeat
    end tell
    error "sesión de iTerm2 no encontrada: " & wanted
end run
"""


def session_uuid(iterm_session_id: str) -> str:
    """`w0t1p0:6A1B...` → `6A1B...`."""
    return iterm_session_id.rsplit(":", 1)[-1]


class ITerm2Target(EnvTerminalTarget):
    name = "iterm2"
    required_env = ("ITERM_SESSION_ID",)

    def matches(self, proc: ClaudeProcess) -> bool:
        # TERM_PROGRAM lo fija el terminal más interno: descarta un ITERM_SESSION_ID heredado
        # por otro terminal abierto desde iTerm2.
        return super().matches(proc) and proc.environ.get("TERM_PROGRAM") == "iTerm.app"

    def describe(self, proc: ClaudeProcess) -> str:
        return f"iTerm2 {proc.environ['ITERM_SESSION_ID'].split(':', 1)[0]}"

    def send_ctrl_v(self, proc: ClaudeProcess) -> None:
        osascript(WRITE_SCRIPT, session_uuid(proc.environ["ITERM_SESSION_ID"]), CTRL_V)

    def window_of(self, proc: ClaudeProcess, windows: list[WindowInfo]) -> WindowInfo | None:
        # Las sesiones cuelgan de iTermServer, no de la ventana: la de iTerm2 usada más
        # recientemente.
        return max(windows, key=lambda w: self._ctx.recency.last_seen(w.id), default=None)

    def _list_windows(self) -> list[WindowInfo]:
        return [w for w in super()._list_windows() if process_name(w.pid) == APP_PROCESS]


@register_target("iterm2", platforms=("macos",))
def build(options: Mapping[str, Any], ctx: TargetContext) -> ITerm2Target:
    return ITerm2Target(ctx)
