"""Composition root: cablea plataforma, destinos y orquestador, y corre el bucle."""

from __future__ import annotations

import logging
import queue

from paste_photo.config import Config
from paste_photo.core.events import ScreenshotCaptured
from paste_photo.core.orchestrator import Orchestrator
from paste_photo.core.ports import TargetStrategy
from paste_photo.platforms.factory import PlatformFactory
from paste_photo.targets import TargetContext, build_target

log = logging.getLogger(__name__)


def build_context(factory: PlatformFactory) -> TargetContext:
    return TargetContext(
        platform=factory.name,
        focus=factory.create_focus_manager(),
        keyboard=factory.create_keyboard(),
    )


def build_targets(config: Config, ctx: TargetContext) -> list[TargetStrategy]:
    return [build_target(options, ctx) for options in config.targets]


def probe(config: Config, factory: PlatformFactory) -> int:
    """Muestra qué destino recibiría la próxima captura, sin pegar nada."""
    found = False
    for target in build_targets(config, build_context(factory)):
        handle = target.locate()
        status = f"-> {handle.label!r}" if handle else "(no encontrado)"
        print(f"{target.name:<18} {status}")
        found = found or handle is not None
    return 0 if found else 1


def run(config: Config, factory: PlatformFactory) -> None:
    ctx = build_context(factory)
    targets = build_targets(config, ctx)
    orchestrator = Orchestrator(
        targets,
        ctx.focus,
        debounce_s=config.debounce_ms / 1000,
        restore_focus=config.restore_focus,
    )
    # El listener corre en su hilo; los pegados se hacen en el principal (UI Automation/COM).
    events: queue.Queue[ScreenshotCaptured] = queue.Queue()
    source = factory.create_screenshot_source()
    source.start(events.put)
    log.info("paste-photo activo (%s). Destinos: %s. Ctrl+C para salir.",
             factory.name, ", ".join(t.name for t in targets))
    try:
        while True:
            try:
                event = events.get(timeout=0.5)  # timeout para que Ctrl+C responda
            except queue.Empty:
                continue
            orchestrator.handle(event)
    except KeyboardInterrupt:
        log.info("Saliendo...")
    finally:
        source.stop()
