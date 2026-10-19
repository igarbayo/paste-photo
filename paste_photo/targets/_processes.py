"""Utilidades de procesos (psutil, multiplataforma)."""

from __future__ import annotations

from collections.abc import Iterable, Iterator

import psutil


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
