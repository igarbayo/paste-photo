# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Icono en la bandeja del sistema (pystray): la interfaz por defecto.

Menú:
    paste-photo: activo          (estado)
    ✔ Activado                   pausa / reanuda
    Pegar en ▸                   el Claude usado por última vez | orden de la configuración
    ✔ Notificaciones
    ¿Dónde pegaría ahora?
    Abrir configuración
    Ver registro
    ✔ Iniciar con Windows        (solo si el SO lo soporta)
    Salir

Para añadir una opción: un `MenuItem` en `_menu()` que llame a un método de este archivo; ese
método habla con el servicio (`service.submit`, `service.pause`...) o guarda un ajuste con
`_save_setting`. Ver `paste_photo/ui/CLAUDE.md`.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from concurrent.futures import TimeoutError as FutureTimeout
from pathlib import Path
from typing import Any

import pystray
from PIL import Image

from paste_photo import resources
from paste_photo.config import Config, save_setting
from paste_photo.core.events import NotPasted, Pasted, ServiceEvent, StateChanged
from paste_photo.core.orchestrator import PREFER_ORDER, PREFER_RECENT
from paste_photo.core.ports import Autostart
from paste_photo.service import PasteService
from paste_photo.ui._system import open_path

log = logging.getLogger(__name__)

APP_TITLE = "paste-photo"
TARGET_NAMES = {"windows_terminal": "Windows Terminal", "browser": "el navegador"}
MAX_LABEL = 60


class TrayApp:
    def __init__(
        self,
        service: PasteService,
        config: Config,
        *,
        config_path: Path,
        log_path: Path,
        autostart: Autostart | None,
        launch_command: str,
        autostart_label: str = "Iniciar con Windows",
    ) -> None:
        self._service = service
        self._config_path = config_path
        self._log_path = log_path
        self._autostart = autostart
        self._launch_command = launch_command
        self._autostart_label = autostart_label
        self._prefer = config.prefer
        self._notify = config.notify
        self._images = _icon_images()
        self._icon: pystray.Icon | None = None

    def run(self) -> None:
        """Bloquea hasta que el usuario elige "Salir"."""
        self._icon = pystray.Icon(APP_TITLE, self._images[True], APP_TITLE, menu=self._menu())
        self._service.subscribe(self._on_event)
        self._icon.run(setup=self._setup)

    def _setup(self, icon: pystray.Icon) -> None:
        icon.visible = True
        try:
            self._service.start()
        except Exception as error:
            log.exception("No se pudo arrancar el servicio")
            self._toast(f"No se pudo arrancar: {error}. Mira el registro.", force=True)
            return
        self._toast("Activo. Haz una captura y aparecerá en Claude.")

    # --- menú --------------------------------------------------------------

    def _menu(self) -> pystray.Menu:
        item = pystray.MenuItem
        items = [
            item(lambda _: f"{APP_TITLE}: {'activo' if self._service.active else 'en pausa'}",
                 None, enabled=False),
            pystray.Menu.SEPARATOR,
            item("Activado", self._toggle_active, checked=lambda _: self._service.active,
                 default=True),
            item("Pegar en", pystray.Menu(
                item("El Claude usado por última vez", self._prefer_setter(PREFER_RECENT),
                     checked=lambda _: self._prefer == PREFER_RECENT, radio=True),
                item("El orden de la configuración", self._prefer_setter(PREFER_ORDER),
                     checked=lambda _: self._prefer == PREFER_ORDER, radio=True),
            )),
            item("Notificaciones", self._toggle_notify, checked=lambda _: self._notify),
            pystray.Menu.SEPARATOR,
            item("¿Dónde pegaría ahora?", self._show_probe),
            item("Abrir configuración", lambda: open_path(self._config_path)),
            item("Ver registro", self._open_log),
        ]
        if self._autostart is not None:
            items.append(item(self._autostart_label, self._toggle_autostart,
                              checked=lambda _: self._autostart_enabled()))
        items += [pystray.Menu.SEPARATOR, item("Salir", self._quit)]
        return pystray.Menu(*items)

    def _toggle_active(self) -> None:
        if self._service.active:
            self._service.pause()
        else:
            self._service.resume()

    def _prefer_setter(self, prefer: str) -> Callable[[], None]:
        def set_prefer() -> None:
            self._prefer = prefer
            self._service.set_prefer(prefer)
            self._save_setting("prefer", prefer)

        return set_prefer

    def _toggle_notify(self) -> None:
        self._notify = not self._notify
        self._save_setting("notify", self._notify)

    def _show_probe(self) -> None:
        try:
            candidates = self._service.probe().result(timeout=15)
        except FutureTimeout:
            self._toast("No se pudo comprobar a tiempo. Inténtalo de nuevo.", force=True)
            return
        if not candidates:
            self._toast("No hay ninguna sesión de Claude abierta.", force=True)
            return
        lines = [f"{n}. {_target_name(t)}: {_short(label)}"
                 for n, (t, label) in enumerate(candidates[:3], start=1)]
        self._toast("Pegaría en:\n" + "\n".join(lines), force=True)

    def _open_log(self) -> None:
        if self._log_path.exists():
            open_path(self._log_path)
        else:
            self._toast("Todavía no hay registro.", force=True)

    def _autostart_enabled(self) -> bool:
        try:
            return self._autostart is not None and self._autostart.is_enabled()
        except Exception:
            log.exception("No se pudo leer el inicio automático")
            return False

    def _toggle_autostart(self) -> None:
        assert self._autostart is not None
        if self._autostart_enabled():
            self._autostart.disable()
        else:
            self._autostart.enable(self._launch_command)

    def _quit(self) -> None:
        self._service.stop()
        if self._icon is not None:
            self._icon.stop()

    # --- eventos del servicio ----------------------------------------------

    def _on_event(self, event: ServiceEvent) -> None:
        if isinstance(event, Pasted):
            self._toast(f"Captura pegada en {_target_name(event.target)}:\n{_short(event.label)}")
        elif isinstance(event, NotPasted):
            self._toast("Captura detectada, pero no hay ningún Claude abierto.")
        elif isinstance(event, StateChanged) and self._icon is not None:
            self._icon.icon = self._images[event.active]
            self._icon.title = f"{APP_TITLE} ({'activo' if event.active else 'en pausa'})"
            self._icon.update_menu()

    # --- helpers -----------------------------------------------------------

    def _toast(self, message: str, *, force: bool = False) -> None:
        if self._icon is not None and (self._notify or force):
            try:
                self._icon.notify(message, APP_TITLE)
            except Exception:
                log.exception("No se pudo mostrar la notificación")

    def _save_setting(self, key: str, value: Any) -> None:
        try:
            save_setting(self._config_path, "general", key, value)
        except Exception:
            log.exception("No se pudo guardar %s en %s", key, self._config_path)


def _icon_images() -> dict[bool, Image.Image]:
    """{activo: icono normal, en pausa: icono en gris}."""
    active = Image.open(resources.path(resources.ICON_PNG)).convert("RGBA")
    gray = active.convert("LA").convert("RGBA")
    gray.putalpha(active.getchannel("A"))
    return {True: active, False: gray}


def _target_name(target: str) -> str:
    return TARGET_NAMES.get(target, target)


def _short(label: str) -> str:
    return label if len(label) <= MAX_LABEL else label[: MAX_LABEL - 1] + "…"
