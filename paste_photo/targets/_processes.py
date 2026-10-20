# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Utilidades de procesos (psutil, multiplataforma)."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass

import psutil

from paste_photo.core.ports import WindowInfo


def processes_named(process_names: Iterable[str]) -> Iterator[psutil.Process]:
    """Procesos vivos con alguno de esos nombres (sin distinguir mayúsculas)."""
    wanted = {n.lower() for n in process_names}
    for proc in psutil.process_iter(["name"]):
        if (proc.info["name"] or "").lower() in wanted:
            yield proc


def ancestor_pids(proc: psutil.Process) -> set[int]:
    try:
        return {p.pid for p in proc.parents()}
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return set()


def ancestor_pids_of(process_names: Iterable[str]) -> set[int]:
    """PIDs de todos los ancestros de los procesos vivos con alguno de esos nombres.

    Sirve para saber qué ventanas (por el PID de su proceso) alojan, directa o
    indirectamente, un proceso concreto, p. ej. `claude.exe` dentro de Windows Terminal.
    """
    ancestors: set[int] = set()
    for proc in processes_named(process_names):
        ancestors |= ancestor_pids(proc)
    return ancestors


def cmdline(proc: psutil.Process) -> list[str]:
    try:
        return proc.cmdline()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return []


def process_name(pid: int) -> str:
    try:
        return psutil.Process(pid).name().lower()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return ""


# --- Claude Code en ejecución (Linux/macOS: incluye su entorno) -------------------------

CLAUDE_NAMES = ("claude", "claude.exe")
CLAUDE_CMDLINE_HINT = "@anthropic-ai/claude-code"  # instalación por npm: `node .../cli.js`
# Apps de escritorio de macOS (Claude.app también se llama "Claude"): no son Claude Code.
MACOS_APP_BUNDLE_HINT = ".app/Contents/MacOS/"
# `claude --chrome-native-host`: el puente de Claude in Chrome, sin terminal ni prompt.
NOT_A_SESSION_ARG = "--chrome-native-host"


def _program_name(argv0: str) -> str:
    return argv0.replace("\\", "/").rsplit("/", 1)[-1].lower()


@dataclass(frozen=True)
class ClaudeProcess:
    pid: int
    environ: dict[str, str]
    ancestors: tuple[int, ...]  # del padre hacia arriba


def is_claude(proc: psutil.Process) -> bool:
    try:
        info = getattr(proc, "info", None) or {}  # solo existe en los de process_iter
        cmdline = (info["cmdline"] if "cmdline" in info else proc.cmdline()) or []
        if cmdline and MACOS_APP_BUNDLE_HINT in cmdline[0] or NOT_A_SESSION_ARG in cmdline:
            return False
        if (info.get("name") or proc.name()).lower() in CLAUDE_NAMES:
            return True
        # Instalador nativo de macOS/Linux: `claude` es un enlace a `versions/<versión>`, así
        # que el proceso se llama como la versión ("2.1.304") y solo argv[0] dice "claude".
        if cmdline and _program_name(cmdline[0]) in CLAUDE_NAMES:
            return True
        return any(CLAUDE_CMDLINE_HINT in part for part in cmdline)
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return False


def claude_processes() -> list[ClaudeProcess]:
    """Procesos de Claude Code del usuario, con su entorno (revela tmux, kitty, Konsole...).

    Se descartan los procesos auxiliares de Claude cuyo padre también es Claude."""
    found: dict[int, ClaudeProcess] = {}
    for proc in psutil.process_iter(["name", "cmdline"]):
        if not is_claude(proc):
            continue
        try:
            parents = proc.parents()
            if any(is_claude(p) for p in parents[:2]):
                continue
            environ = proc.environ()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        found[proc.pid] = ClaudeProcess(proc.pid, environ, tuple(p.pid for p in parents))
    return list(found.values())


def owning_window(ancestors: Iterable[int], windows: Iterable[WindowInfo]) -> WindowInfo | None:
    """Primera ventana cuyo proceso es un ancestro (el emulador de terminal)."""
    by_pid: dict[int, WindowInfo] = {}
    for window in windows:
        by_pid.setdefault(window.pid, window)
    for pid in ancestors:
        if pid in by_pid:
            return by_pid[pid]
    return None
