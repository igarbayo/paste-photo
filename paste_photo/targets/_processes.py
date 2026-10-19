"""Utilidades de procesos (psutil, multiplataforma)."""

from __future__ import annotations

from collections.abc import Iterable

import psutil


def ancestor_pids_of(process_names: Iterable[str]) -> set[int]:
    """PIDs de todos los ancestros de los procesos vivos con alguno de esos nombres.

    Sirve para saber qué ventanas (por el PID de su proceso) alojan, directa o
    indirectamente, un proceso concreto, p. ej. `claude.exe` dentro de Windows Terminal.
    """
    wanted = {n.lower() for n in process_names}
    ancestors: set[int] = set()
    for proc in psutil.process_iter(["name"]):
        try:
            if (proc.info["name"] or "").lower() in wanted:
                ancestors.update(p.pid for p in proc.parents())
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return ancestors


def process_name(pid: int) -> str:
    try:
        return psutil.Process(pid).name().lower()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return ""
