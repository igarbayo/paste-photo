"""Utilidades de aplicación compartidas por las interfaces: instancia única, sondeo, logs y
la orden con la que el SO debe relanzar la app (inicio automático)."""

from __future__ import annotations

import logging
import logging.handlers
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from paste_photo.config import Config
from paste_photo.platforms.factory import PlatformFactory
from paste_photo.service import build_context, build_orchestrator

log = logging.getLogger(__name__)

LOCK_FILENAME = "paste-photo.lock"


class AlreadyRunningError(RuntimeError):
    pass


def probe(config: Config, factory: PlatformFactory) -> list[tuple[str, str]]:
    """Dónde se intentaría pegar ahora, sin pegar nada.

    Sin historial de uso, solo cuenta la ventana activa en este momento."""
    with factory.worker_context():
        ctx = build_context(factory)
        ctx.recency.touch(ctx.focus.capture())
        return [(t.name, h.label) for t, h in build_orchestrator(config, ctx).candidates()]


@contextmanager
def single_instance() -> Iterator[None]:
    """Impide dos instancias a la vez: pegarían dos veces y quizá en sitios distintos."""
    path = Path(tempfile.gettempdir()) / LOCK_FILENAME
    handle = path.open("a+")
    try:
        _lock(handle)
    except OSError:
        handle.close()
        raise AlreadyRunningError(
            "paste-photo ya se está ejecutando (cierra la otra instancia primero)"
        ) from None
    try:
        yield
    finally:
        handle.close()  # el SO libera el bloqueo al cerrar o al morir el proceso


def _lock(handle) -> None:
    if sys.platform == "win32":
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def launch_command() -> str:
    """Orden para arrancar la app en modo bandeja (la usa el inicio automático)."""
    if getattr(sys, "frozen", False):  # .exe de PyInstaller
        return f'"{sys.executable}"'
    python = Path(sys.executable)
    pythonw = python.with_name("pythonw.exe")  # sin ventana de consola en Windows
    interpreter = pythonw if pythonw.exists() else python
    return f'"{interpreter}" -m paste_photo'


def setup_logging(log_file: Path | None, *, console: bool, debug: bool) -> None:
    """Archivo rotativo (siempre que haya ruta) + consola (modo `run`)."""
    handlers: list[logging.Handler] = []
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(
            logging.handlers.RotatingFileHandler(
                log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
            )
        )
    if console and sys.stderr is not None:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers or [logging.NullHandler()],
        force=True,
    )
    logging.getLogger("comtypes").setLevel(logging.WARNING)  # ruido de uiautomation
    logging.getLogger("PIL").setLevel(logging.WARNING)
