"""Claude Code CLI dentro de una pestaña de Windows Terminal."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from paste_photo.targets._win_uia import UiaTabTarget
from paste_photo.targets.registry import TargetContext, register_target

log = logging.getLogger(__name__)

WT_WINDOW_CLASS = "CASCADIA_HOSTING_WINDOW_CLASS"
# Claude Code pone en el título un glifo de estado: ✳ en reposo, ◐◓◑◒ trabajando.
DEFAULT_TITLE_REGEX = r"^[✳✻✽✶✢·◐◓◑◒]\s|Claude Code"
DEFAULT_PASTE_KEYS = "alt+v"  # Ctrl+V en Windows Terminal solo pega texto
DEFAULT_PROCESS_NAMES = ("claude.exe", "claude")


class WindowsTerminalTarget(UiaTabTarget):
    name = "windows_terminal"
    tab_search_depth = 8

    def __init__(
        self,
        ctx: TargetContext,
        *,
        require_process: bool = True,
        process_names: tuple[str, ...] = DEFAULT_PROCESS_NAMES,
        **kwargs: Any,
    ) -> None:
        super().__init__(ctx, **kwargs)
        self._require_process = require_process
        self._process_names = process_names

    def _candidate_windows(self) -> list[int]:
        windows = self._windows_of_class(WT_WINDOW_CLASS)
        if not self._require_process:
            return windows
        # Una pestaña conserva su título aunque Claude haya terminado: exigimos que el
        # proceso de esa ventana de WT tenga un `claude` vivo entre sus descendientes.
        from paste_photo.targets._processes import ancestor_pids_of

        hosts = ancestor_pids_of(self._process_names)
        alive = [w for w in windows if self._window_pid(w) in hosts]
        if len(alive) < len(windows):
            log.debug("Ventanas de WT sin Claude vivo descartadas: %d", len(windows) - len(alive))
        return alive


@register_target("windows_terminal")
def build(options: Mapping[str, Any], ctx: TargetContext) -> WindowsTerminalTarget:
    if ctx.platform != "windows":
        raise ValueError("El destino windows_terminal solo funciona en Windows")
    return WindowsTerminalTarget(
        ctx,
        title_regex=options.get("title_regex", DEFAULT_TITLE_REGEX),
        paste_keys=options.get("paste_keys", DEFAULT_PASTE_KEYS),
        settle_ms=int(options.get("settle_ms", 150)),
        restore_tab=bool(options.get("restore_tab", True)),
        require_process=bool(options.get("require_process", True)),
        process_names=tuple(options.get("process_names", DEFAULT_PROCESS_NAMES)),
    )
