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
        wsl: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(ctx, **kwargs)
        self._require_process = require_process
        self._process_names = process_names
        self._wsl = wsl

    def _candidate_windows(self) -> list[int]:
        windows = self._windows_of_class(WT_WINDOW_CLASS)
        if not self._require_process:
            return windows
        # Una pestaña conserva su título aunque Claude haya terminado: exigimos que el
        # proceso de esa ventana de WT tenga un `claude` vivo entre sus descendientes.
        from paste_photo.targets._processes import ancestor_pids_of

        hosts = ancestor_pids_of(self._process_names)
        pending = {self._window_pid(w) for w in windows} - hosts
        if self._wsl and pending:
            hosts |= self._wsl_hosts(pending)
        alive = [w for w in windows if self._window_pid(w) in hosts]
        if len(alive) < len(windows):
            log.debug("Ventanas de WT sin Claude vivo descartadas: %d", len(windows) - len(alive))
        return alive

    @staticmethod
    def _wsl_hosts(window_pids: set[int]) -> set[int]:
        """Ancestros de los `wsl.exe` (bajo esas ventanas) cuya distro ejecuta Claude.

        Desde Windows no se ve el `claude` de WSL: se pregunta a la distro. Si no se puede
        comprobar, se acepta (el título de la pestaña ya coincidió)."""
        from paste_photo.targets import _wsl
        from paste_photo.targets._processes import ancestor_pids, cmdline, processes_named

        hosts: set[int] = set()
        checked: dict[str | None, bool | None] = {}
        for proc in processes_named(_wsl.WSL_PROCESS_NAMES):
            ancestors = ancestor_pids(proc)
            if not ancestors & window_pids:
                continue
            distro = _wsl.distro_from_cmdline(cmdline(proc))
            if distro not in checked:
                checked[distro] = _wsl.claude_running_in(distro)
                log.debug("WSL %s: claude = %s", distro or "(por defecto)", checked[distro])
            if checked[distro] is not False:
                hosts |= ancestors
        return hosts


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
        wsl=bool(options.get("wsl", True)),
    )
