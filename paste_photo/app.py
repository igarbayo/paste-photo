"""Composition root: cablea plataforma, destinos y orquestador, y corre el bucle."""

from __future__ import annotations

import logging
import queue
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from paste_photo.config import Config
from paste_photo.core.events import ScreenshotCaptured
from paste_photo.core.orchestrator import Orchestrator
from paste_photo.core.ports import TargetStrategy
from paste_photo.core.recency import Recency
from paste_photo.platforms.factory import PlatformFactory
from paste_photo.targets import TargetContext, build_target

log = logging.getLogger(__name__)

LOCK_FILENAME = "paste-photo.lock"
FOCUS_POLL_S = 0.25  # cada cuánto se apunta la ventana activa (para "el Claude más reciente")


class AlreadyRunningError(RuntimeError):
    pass


def build_context(factory: PlatformFactory) -> TargetContext:
    return TargetContext(
        platform=factory.name,
        focus=factory.create_focus_manager(),
        keyboard=factory.create_keyboard(),
        recency=Recency(),
    )


def build_targets(config: Config, ctx: TargetContext) -> list[TargetStrategy]:
    return [build_target(options, ctx) for options in config.targets]


def build_orchestrator(config: Config, ctx: TargetContext) -> Orchestrator:
    return Orchestrator(
        build_targets(config, ctx),
        ctx.focus,
        recency=ctx.recency,
        prefer=config.prefer,
        remember_images=config.remember_images,
        restore_focus=config.restore_focus,
    )


def probe(config: Config, factory: PlatformFactory) -> int:
    """Muestra, en orden, dónde se intentaría pegar la próxima captura, sin pegar nada.

    Sin historial de uso, solo cuenta la ventana activa ahora (la terminal desde la que
    lo lanzas, normalmente)."""
    ctx = build_context(factory)
    ctx.recency.touch(ctx.focus.capture())
    candidates = build_orchestrator(config, ctx).candidates()
    if not candidates:
        print("No hay ninguna sesión de Claude abierta")
        return 1
    for position, (target, handle) in enumerate(candidates, start=1):
        print(f"{position}. {target.name:<18} -> {handle.label!r}")
    return 0


def run(config: Config, factory: PlatformFactory) -> None:
    with single_instance():
        _run(config, factory)


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


def _run(config: Config, factory: PlatformFactory) -> None:
    ctx = build_context(factory)
    orchestrator = build_orchestrator(config, ctx)
    # El listener corre en su hilo; los pegados se hacen en el principal (UI Automation/COM).
    events: queue.Queue[ScreenshotCaptured] = queue.Queue()
    source = factory.create_screenshot_source()
    source.start(events.put)
    log.info("paste-photo activo (%s). Destinos: %s (prioridad: %s). Ctrl+C para salir.",
             factory.name, ", ".join(t["type"] for t in config.targets), config.prefer)
    try:
        while True:
            # Mismo hilo que los pegados: mientras se pega no se registra el foco "prestado".
            ctx.recency.touch(ctx.focus.capture())
            try:
                event = events.get(timeout=FOCUS_POLL_S)  # timeout: Ctrl+C sigue respondiendo
            except queue.Empty:
                continue
            orchestrator.handle(event)
    except KeyboardInterrupt:
        log.info("Saliendo...")
    finally:
        source.stop()
