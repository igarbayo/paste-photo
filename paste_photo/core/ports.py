# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Puertos (interfaces) que los adaptadores de cada SO y de cada destino implementan."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from paste_photo.core.events import ScreenshotCaptured


@dataclass(frozen=True)
class TargetHandle:
    """Referencia opaca a un destino localizado (ventana + datos propios del destino)."""

    window_id: int
    label: str
    extra: dict[str, Any] = field(default_factory=dict, compare=False)


@runtime_checkable
class ScreenshotSource(Protocol):
    """Fuente de capturas (Observer: notifica a `on_capture` por cada captura nueva).

    `start` no debe bloquear: lanza su propio hilo/bucle. `on_capture` puede
    llamarse desde otro hilo, así que debe ser thread-safe (p. ej. `queue.put`).
    """

    def start(self, on_capture: Callable[[ScreenshotCaptured], None]) -> None: ...

    def stop(self) -> None: ...


@runtime_checkable
class Keyboard(Protocol):
    """Envía combinaciones de teclas a la ventana con el foco."""

    def send_hotkey(self, hotkey: str) -> None: ...


@runtime_checkable
class FocusManager(Protocol):
    """Gestiona el foco de ventanas. `capture`/`restore` implementan un Memento."""

    def capture(self) -> Any: ...

    def restore(self, snapshot: Any) -> None: ...

    def activate(self, window_id: int) -> None: ...


@runtime_checkable
class Autostart(Protocol):
    """Arranque automático al iniciar sesión en el SO."""

    def is_enabled(self) -> bool: ...

    def enable(self, command: str) -> None: ...

    def disable(self) -> None: ...


@runtime_checkable
class TargetStrategy(Protocol):
    """Un sitio donde puede estar Claude Code (terminal, app, navegador...)."""

    name: str

    def locate(self) -> TargetHandle | None:
        """Devuelve el destino si Claude Code está abierto aquí; si no, None."""
        ...

    def paste(self, handle: TargetHandle) -> None:
        """Lleva el foco al destino y pega la imagen del portapapeles (sin Enter)."""
        ...


@contextmanager
def preserve_focus(focus: FocusManager) -> Iterator[None]:
    """Guarda la ventana activa y la restaura al salir, incluso si hay error."""
    snapshot = focus.capture()
    try:
        yield
    finally:
        focus.restore(snapshot)
