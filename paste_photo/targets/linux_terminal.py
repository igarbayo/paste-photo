# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Claude Code en cualquier terminal de Linux sin IPC (GNOME Terminal, Ptyxis, xterm,
Alacritty, Tilix...): ventana del terminal → foco → Ctrl+V.

Necesita el sistema de ventanas de la sesión (`ctx.windows`: X11, GNOME Shell o KWin).
No puede cambiar de pestaña: solo pega si la pestaña de Claude es la activa de su ventana,
lo que se sabe por el título (Claude Code lo prefija con ✳ o ◐◓◑◒). Los procesos que
cubre un destino IPC (tmux, kitty, WezTerm, Konsole) se dejan a ese destino.
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
from paste_photo.targets._processes import claude_processes, owner_windows
from paste_photo.targets.registry import TargetContext, register_target

log = logging.getLogger(__name__)

DEFAULT_TITLE_REGEX = r"^[✳✻✽✶✢·◐◓◑◒]\s|Claude Code"
DEFAULT_PASTE_KEYS = "ctrl+v"  # en Linux Claude Code pega imágenes con Ctrl+V


class LinuxTerminalTarget:
    name = "linux_terminal"

    def __init__(self, ctx: TargetContext, *, title_regex: str = DEFAULT_TITLE_REGEX,
                 paste_keys: str = DEFAULT_PASTE_KEYS, settle_ms: int = 150,
                 require_title: bool = True) -> None:
        self._ctx = ctx
        self._title_re = re.compile(title_regex)
        self._paste_keys = paste_keys
        self._settle_s = settle_ms / 1000
        self._require_title = require_title

    def locate(self) -> TargetHandle | None:
        if self._ctx.windows is None:
            return None
        procs = [p for p in claude_processes() if not handled_by_ipc(p.environ)]
        if not procs:
            return None
        windows = self._ctx.windows.list_windows()
        handles: dict[int, TargetHandle] = {}
        for proc in procs:
            # GNOME Terminal, Ptyxis, Tilix...: un proceso para todas sus ventanas. La de
            # este Claude es una con su título (la primera del proceso podía ser otra).
            owned = owner_windows(proc.ancestors, windows)
            if self._require_title:
                titled = [w for w in owned if self._title_re.search(w.title)]
                if owned and not titled:
                    log.debug("Claude en %r no es la pestaña activa: se omite", owned[0].title)
                owned = titled
            else:
                owned = owned[:1]
            for window in owned:
                if window.id not in handles:
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


@register_target("linux_terminal", platforms=("linux",))
def build(options: Mapping[str, Any], ctx: TargetContext) -> LinuxTerminalTarget:
    return LinuxTerminalTarget(
        ctx,
        title_regex=options.get("title_regex", DEFAULT_TITLE_REGEX),
        paste_keys=options.get("paste_keys", DEFAULT_PASTE_KEYS),
        settle_ms=int(options.get("settle_ms", 150)),
        require_title=bool(options.get("require_title", True)),
    )
