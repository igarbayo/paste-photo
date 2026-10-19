# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Claude Code dentro de WSL: desde Windows solo se ve `wsl.exe`, no `claude`.

Se pregunta a la distro (con `wsl.exe -d <distro> -e sh -c ...`) si hay un `claude` vivo.
"""

from __future__ import annotations

import logging
import subprocess
from collections.abc import Callable, Sequence

log = logging.getLogger(__name__)

WSL_PROCESS_NAMES = ("wsl.exe",)
# `[c]laude-code` evita que pgrep -f se encuentre a sí mismo (su línea de órdenes
# contiene el patrón literal, no "claude-code").
_CHECK_SCRIPT = "pgrep -x claude >/dev/null 2>&1 || pgrep -f '[c]laude-code' >/dev/null 2>&1"
_CREATE_NO_WINDOW = 0x08000000

Runner = Callable[..., subprocess.CompletedProcess]


def distro_from_cmdline(cmdline: Sequence[str]) -> str | None:
    """Distro pedida en la línea de órdenes de wsl.exe (`-d X`, `--distribution X`,
    `--distribution=X`); None = distro por defecto."""
    args = list(cmdline[1:])
    for i, arg in enumerate(args):
        if arg in ("-d", "--distribution") and i + 1 < len(args):
            return args[i + 1]
        if arg.startswith("--distribution="):
            return arg.split("=", 1)[1]
    return None


def check_command(distro: str | None) -> list[str]:
    cmd = ["wsl.exe"]
    if distro:
        cmd += ["-d", distro]
    return cmd + ["-e", "sh", "-c", _CHECK_SCRIPT]


def claude_running_in(
    distro: str | None, *, runner: Runner = subprocess.run, timeout_s: float = 3.0
) -> bool | None:
    """True/False si se pudo comprobar; None si no (WSL no responde, error...)."""
    try:
        result = runner(
            check_command(distro),
            capture_output=True,
            timeout=timeout_s,
            creationflags=_CREATE_NO_WINDOW,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        log.debug("No se pudo comprobar WSL (%s): %s", distro or "por defecto", error)
        return None
    if result.returncode in (0, 1):  # códigos de pgrep: 0 encontrado, 1 no encontrado
        return result.returncode == 0
    return None
