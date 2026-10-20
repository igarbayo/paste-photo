# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Claude Code en cualquier otro terminal de macOS (Ghostty, Alacritty, Warp, Hyper, Tabby,
kitty sin control remoto...): ventana del terminal → foco → Ctrl+V.

Como `linux_terminal`: no puede cambiar de pestaña, así que solo pega en una ventana del
terminal cuyo título es el de Claude Code (✳ o ◐◓◑◒: la pestaña de Claude es la activa).
Una app de macOS tiene todas sus ventanas en un mismo proceso, por eso se buscan entre las
ventanas de ese proceso las que tienen ese título. Terminal.app e iTerm2 tienen destinos
propios (`terminal_app`, `iterm2`) y los procesos con IPC (tmux, kitty, WezTerm, Orca), el suyo.
"""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Mapping
from typing import Any

from paste_photo.core.events import ScreenshotCaptured
from paste_photo.core.ports import TargetHandle
from paste_photo.targets._env_terminal import handled_by_ipc
from paste_photo.targets._processes import claude_processes
from paste_photo.targets.linux_terminal import DEFAULT_TITLE_REGEX
from paste_photo.targets.registry import TargetContext, register_target

log = logging.getLogger(__name__)

DEFAULT_PASTE_KEYS = "ctrl+v"  # también en macOS: Cmd+V lo captura el terminal (solo texto)
# TERM_PROGRAM de los terminales con destino propio.
SCRIPTED_TERMINALS = ("Apple_Terminal", "iTerm.app")


class MacTerminalTarget:
    name = "macos_terminal"

    def __init__(self, ctx: TargetContext, *, title_regex: str = DEFAULT_TITLE_REGEX,
                 paste_keys: str = DEFAULT_PASTE_KEYS, settle_ms: int = 150) -> None:
        self._ctx = ctx
        self._title_re = re.compile(title_regex)
        self._paste_keys = paste_keys
        self._settle_s = settle_ms / 1000

    def locate(self) -> TargetHandle | None:
        if self._ctx.windows is None:
            return None
        procs = [p for p in claude_processes() if not handled_by_ipc(p.environ)
                 and p.environ.get("TERM_PROGRAM") not in SCRIPTED_TERMINALS]
        if not procs:
            return None
        windows = self._ctx.windows.list_windows()
        handles: dict[int, TargetHandle] = {}
        for proc in procs:
            ancestors = set(proc.ancestors)
            for window in windows:
                if window.pid in ancestors and window.id not in handles \
                        and self._title_re.search(window.title):
                    handles[window.id] = TargetHandle(window.id, window.title, {"pid": proc.pid})
        if not handles:
            return None
        ordered = sorted(handles.values(),
                         key=lambda h: self._ctx.recency.last_seen(h.window_id), reverse=True)
        best = ordered[0]
        return TargetHandle(best.window_id, best.label, {**best.extra, "candidates": ordered})

    def paste(self, handle: TargetHandle, shot: ScreenshotCaptured | None = None) -> None:
        assert self._ctx.windows is not None
        self._ctx.windows.activate(handle.window_id)
        time.sleep(self._settle_s)
        self._ctx.keyboard.send_hotkey(self._paste_keys)
        time.sleep(self._settle_s)


@register_target("macos_terminal", platforms=("macos",))
def build(options: Mapping[str, Any], ctx: TargetContext) -> MacTerminalTarget:
    return MacTerminalTarget(
        ctx,
        title_regex=options.get("title_regex", DEFAULT_TITLE_REGEX),
        paste_keys=options.get("paste_keys", DEFAULT_PASTE_KEYS),
        settle_ms=int(options.get("settle_ms", 150)),
    )
