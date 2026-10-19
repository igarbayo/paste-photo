"""Modo consola: el servicio en primer plano, con logs en pantalla. Ctrl+C para salir."""

from __future__ import annotations

import logging
import threading

from paste_photo.service import PasteService

log = logging.getLogger(__name__)


def run_console(service: PasteService) -> None:
    service.start()
    log.info("Ctrl+C para salir.")
    stop = threading.Event()
    try:
        while not stop.wait(0.5):  # espera con timeout para que Ctrl+C responda
            pass
    except KeyboardInterrupt:
        log.info("Saliendo...")
    finally:
        service.stop()
