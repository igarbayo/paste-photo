# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Servicio en segundo plano: el motor que comparten todas las interfaces (bandeja, consola...).

Un hilo de trabajo hace todo lo que toca el SO (UI Automation, foco, teclado): procesa las
capturas, apunta la ventana activa para la prioridad por uso reciente y ejecuta las órdenes
que le mandan las interfaces (`submit`). Las interfaces nunca tocan los adaptadores
directamente: llaman a métodos del servicio y se suscriben a sus eventos (`subscribe`).
"""

from __future__ import annotations

import logging
import queue
import threading
from collections.abc import Callable
from concurrent.futures import Future
from typing import Any, TypeVar

from paste_photo.config import Config
from paste_photo.core.events import ScreenshotCaptured, ServiceEvent, StateChanged
from paste_photo.core.orchestrator import Orchestrator
from paste_photo.platforms.factory import PlatformFactory
from paste_photo.targets import TargetContext, available_targets, build_target, supports

log = logging.getLogger(__name__)

T = TypeVar("T")
Listener = Callable[[ServiceEvent], None]

FOCUS_POLL_S = 0.25  # cada cuánto se apunta la ventana activa (prioridad "recent")


class PasteService:
    def __init__(self, config: Config, factory: PlatformFactory) -> None:
        self._config = config
        self._factory = factory
        self._queue: queue.Queue[ScreenshotCaptured | _Command | None] = queue.Queue()
        self._listeners: list[Listener] = []
        self._active = threading.Event()
        self._active.set()
        self._ready = threading.Event()
        self._thread: threading.Thread | None = None
        self._source = None
        self._orchestrator: Orchestrator | None = None
        self._startup_error: BaseException | None = None

    # --- ciclo de vida -----------------------------------------------------

    def start(self) -> None:
        self._thread = threading.Thread(target=self._work, name="paste-photo-worker", daemon=True)
        self._thread.start()
        self._ready.wait(timeout=30)
        if self._startup_error is not None:
            raise self._startup_error
        self._source = self._factory.create_screenshot_source()
        self._source.start(self._on_capture)
        log.info(
            "PastePhoto activo (%s). Destinos: %s (prioridad: %s)",
            self._factory.name,
            ", ".join(self._orchestrator.target_names) if self._orchestrator else "-",
            self._config.prefer,
        )

    def stop(self) -> None:
        if self._source is not None:
            self._source.stop()
            self._source = None
        if self._thread is not None:
            self._queue.put(None)
            self._thread.join(timeout=5)
            self._thread = None

    # --- estado ------------------------------------------------------------

    @property
    def active(self) -> bool:
        return self._active.is_set()

    def pause(self) -> None:
        self._set_active(False)

    def resume(self) -> None:
        self._set_active(True)

    def _set_active(self, active: bool) -> None:
        if active == self.active:
            return
        (self._active.set if active else self._active.clear)()
        log.info("PastePhoto %s", "activado" if active else "en pausa")
        self._emit(StateChanged(active))

    # --- órdenes desde las interfaces ---------------------------------------

    def submit(self, fn: Callable[[Orchestrator], T]) -> Future[T]:
        """Ejecuta `fn(orquestador)` en el hilo de trabajo (donde se puede tocar el SO)."""
        command = _Command(fn)
        self._queue.put(command)
        return command.future

    def set_prefer(self, prefer: str) -> Future[None]:
        def apply(orchestrator: Orchestrator) -> None:
            orchestrator.prefer = prefer

        return self.submit(apply)

    def probe(self) -> Future[list[tuple[str, str]]]:
        """Dónde se intentaría pegar ahora: [(destino, pestaña), ...] en orden."""
        return self.submit(lambda o: [(t.name, h.label) for t, h in o.candidates()])

    # --- eventos -----------------------------------------------------------

    def subscribe(self, listener: Listener) -> None:
        self._listeners.append(listener)

    def _emit(self, event: ServiceEvent) -> None:
        for listener in list(self._listeners):
            try:
                listener(event)
            except Exception:
                log.exception("Error en un suscriptor del servicio")

    # --- hilo de trabajo ---------------------------------------------------

    def _on_capture(self, event: ScreenshotCaptured) -> None:
        # Llega desde el hilo del portapapeles: solo encolar.
        if self.active:
            self._queue.put(event)
        else:
            log.debug("Captura ignorada: PastePhoto está en pausa")

    def _work(self) -> None:
        try:
            with self._factory.worker_context():
                ctx = build_context(self._factory)
                self._orchestrator = build_orchestrator(self._config, ctx)
                self._ready.set()
                self._loop(ctx)
        except BaseException as error:  # noqa: BLE001 - se re-lanza en start()
            self._startup_error = error
            self._ready.set()
            if self._orchestrator is not None:
                log.exception("El hilo de trabajo terminó por un error")

    def _loop(self, ctx: TargetContext) -> None:
        assert self._orchestrator is not None
        while True:
            # Mismo hilo que los pegados: mientras se pega no se registra el foco "prestado".
            ctx.recency.touch(ctx.focus.capture())
            try:
                item = self._queue.get(timeout=FOCUS_POLL_S)
            except queue.Empty:
                continue
            if item is None:
                return
            if isinstance(item, _Command):
                item.run(self._orchestrator)
                continue
            result = self._orchestrator.handle(item)
            if result is not None:
                self._emit(result)


class _Command:
    def __init__(self, fn: Callable[[Orchestrator], Any]) -> None:
        self.fn = fn
        self.future: Future[Any] = Future()

    def run(self, orchestrator: Orchestrator) -> None:
        try:
            self.future.set_result(self.fn(orchestrator))
        except Exception as error:
            self.future.set_exception(error)


# --- construcción (composition root compartido) ------------------------------


def build_context(factory: PlatformFactory) -> TargetContext:
    return TargetContext(
        platform=factory.name,
        focus=factory.create_focus_manager(),
        keyboard=factory.create_keyboard(),
        windows=factory.create_window_system(),
    )


def build_targets(config: Config, ctx: TargetContext) -> list:
    """Destinos de la config que funcionan en este SO (el resto se omite en silencio)."""
    targets = []
    for options in config.targets:
        kind = options.get("type")
        if not supports(kind, ctx.platform) and kind in available_targets():
            log.debug("Destino %s omitido: no funciona en %s", kind, ctx.platform)
            continue
        targets.append(build_target(options, ctx))
    return targets


def build_orchestrator(config: Config, ctx: TargetContext) -> Orchestrator:
    return Orchestrator(
        build_targets(config, ctx),
        ctx.focus,
        recency=ctx.recency,
        prefer=config.prefer,
        remember_images=config.remember_images,
        restore_focus=config.restore_focus,
    )
