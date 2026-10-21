# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Claude Code en una terminal de Orca (stablyai/orca), en Windows, macOS y Linux.

Orca exporta a sus terminales `ORCA_TERMINAL_HANDLE` (el handle exacto de esa terminal) y
trae una CLI: `orca terminal send --terminal <handle> --text <bytes>` escribe en el PTY sin
foco ni pestaña visible. Se envía la tecla de pegado de Claude Code (Alt+V en Windows,
Ctrl+V en macOS y Linux) y Claude inserta `[Image #N]` en su cursor. Nunca `--enter`.
"""

from __future__ import annotations

import os
import shutil
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from paste_photo.core.ports import WindowInfo
from paste_photo.targets._env_terminal import CTRL_V, EnvTerminalTarget, run
from paste_photo.targets._processes import ClaudeProcess, process_name
from paste_photo.targets.registry import TargetContext, register_target

ALT_V = "\x1bv"  # en un PTY, Alt+V llega como ESC + v
# Proceso de la ventana de Orca (Electron). El daemon que aloja los PTY y la CLI se llaman
# igual pero no tienen ventanas, así que no estorban. En Linux es `orca-ide`: `orca` es el
# lector de pantalla de GNOME. En macOS, la app `Orca` (psutil, en minúsculas).
DEFAULT_APP_NAMES = ("orca.exe", "orca-ide")
MACOS_APP_NAMES = ("orca",)


def default_app_names(platform: str) -> tuple[str, ...]:
    return MACOS_APP_NAMES if platform == "macos" else DEFAULT_APP_NAMES


def default_cli_name() -> str:
    if sys.platform == "win32":
        return "orca.exe"  # no `orca.cmd`: cmd.exe reinterpreta lo que se le pasa
    return "orca" if sys.platform == "darwin" else "orca-ide"


def default_paste_text(platform: str) -> str:
    # Claude Code pega imágenes con Alt+V en Windows y con Ctrl+V en Linux/macOS.
    return ALT_V if platform == "windows" else CTRL_V


def known_cli_paths() -> list[Path]:
    """Dónde instala Orca su CLI cuando no está en el PATH."""
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        return [Path(local, "Programs", "orca", "resources", "bin", "orca.exe")] if local else []
    if sys.platform == "darwin":
        bundle = "Orca.app/Contents/Resources/bin/orca"
        return [Path("/Applications", bundle), Path.home() / "Applications" / bundle]
    return [Path("/usr/bin/orca-ide"), Path("/opt/Orca/resources/bin/orca-ide"),
            Path.home() / ".local/bin/orca-ide"]


class OrcaTarget(EnvTerminalTarget):
    name = "orca"
    required_env = ("ORCA_TERMINAL_HANDLE",)

    def __init__(self, ctx: TargetContext, *, paste_text: str | None = None, cli: str = "",
                 app_names: tuple[str, ...] | None = None) -> None:
        super().__init__(ctx)
        self._paste_text = paste_text if paste_text is not None else default_paste_text(
            ctx.platform)
        self._cli = cli
        self._app_names = {n.lower() for n in (app_names or default_app_names(ctx.platform))}

    def describe(self, proc: ClaudeProcess) -> str:
        return f"Orca {proc.environ['ORCA_TERMINAL_HANDLE']}"

    def send_ctrl_v(self, proc: ClaudeProcess) -> None:
        run([self.cli_for(proc), "terminal", "send", "--terminal",
             proc.environ["ORCA_TERMINAL_HANDLE"], "--text", self._paste_text, "--json"])

    def cli_for(self, proc: ClaudeProcess) -> str:
        """La CLI configurada, la del PATH de esa terminal (Orca lo añade y exporta su
        nombre en `ORCA_CLI_COMMAND`), la del nuestro o la de la ruta de instalación."""
        if self._cli:
            return self._cli
        if sys.platform == "win32":
            exe = default_cli_name()
        else:
            exe = proc.environ.get("ORCA_CLI_COMMAND") or default_cli_name()
        for path in (proc.environ.get("PATH"), None):
            if found := shutil.which(exe, path=path):
                return found
        for candidate in known_cli_paths():
            if candidate.is_file():
                return str(candidate)
        raise RuntimeError("no se encuentra la CLI de Orca (opción `cli` en config.toml)")

    # --- ventana de Orca (para saber cuándo la usaste) ------------------------

    def window_of(self, proc: ClaudeProcess, windows: list[WindowInfo]) -> WindowInfo | None:
        # Los PTY cuelgan del daemon de Orca, no de su ventana: vale cualquier ventana de
        # Orca, la usada más recientemente.
        return self.most_recent(windows)

    def _list_windows(self) -> list[WindowInfo]:
        windows = _win32_windows() if self._ctx.platform == "windows" else super()._list_windows()
        return [w for w in windows if process_name(w.pid) in self._app_names]


def _win32_windows() -> list[WindowInfo]:
    import win32gui
    import win32process

    found: list[WindowInfo] = []

    def collect(hwnd: int, _: Any) -> None:
        if win32gui.IsWindowVisible(hwnd) and (title := win32gui.GetWindowText(hwnd)):
            found.append(WindowInfo(hwnd, title, win32process.GetWindowThreadProcessId(hwnd)[1]))

    win32gui.EnumWindows(collect, None)
    return found


@register_target("orca", platforms=("windows", "macos", "linux"))
def build(options: Mapping[str, Any], ctx: TargetContext) -> OrcaTarget:
    return OrcaTarget(
        ctx,
        paste_text=options.get("paste_text"),
        cli=options.get("cli", ""),
        app_names=tuple(options["app_names"]) if "app_names" in options else None,
    )
