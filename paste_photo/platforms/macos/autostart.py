# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Inicio al iniciar sesión en macOS: un LaunchAgent del usuario
(`~/Library/LaunchAgents/io.github.igarbayo.paste-photo.plist`, sin permisos de administrador).

launchd arranca los agentes con un PATH mínimo (`/usr/bin:/bin:/usr/sbin:/sbin`): se guarda
el PATH actual más el de Homebrew para que se encuentren `tmux`, `kitty`, `wezterm`...
"""

from __future__ import annotations

import os
import plistlib
import shlex
from pathlib import Path

LABEL = "io.github.igarbayo.paste-photo"
EXTRA_PATH = ("/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin", "/usr/sbin", "/sbin")


def launch_agents_dir() -> Path:
    return Path.home() / "Library" / "LaunchAgents"


def agent_path(current: str | None = None) -> str:
    parts = [p for p in (current if current is not None else os.environ.get("PATH", ""))
             .split(os.pathsep) if p]
    return os.pathsep.join(dict.fromkeys(parts + list(EXTRA_PATH)))


def launch_agent(command: str, path: str) -> bytes:
    return plistlib.dumps({
        "Label": LABEL,
        "ProgramArguments": shlex.split(command),
        "RunAtLoad": True,
        "ProcessType": "Interactive",
        "LimitLoadToSessionType": "Aqua",  # solo en sesiones gráficas
        "EnvironmentVariables": {"PATH": path, "LANG": os.environ.get("LANG", "en_US.UTF-8")},
    })


class LaunchAgentAutostart:
    def __init__(self, folder: Path | None = None) -> None:
        self._file = (folder or launch_agents_dir()) / f"{LABEL}.plist"

    def is_enabled(self) -> bool:
        return self._file.exists()

    def enable(self, command: str) -> None:
        self._file.parent.mkdir(parents=True, exist_ok=True)
        self._file.write_bytes(launch_agent(command, agent_path()))

    def disable(self) -> None:
        self._file.unlink(missing_ok=True)
