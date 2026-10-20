# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Ventanas y foco en macOS con la API de Accesibilidad (AX). Necesita ese permiso.

- Qué apps tienen ventanas: `CGWindowListCopyWindowInfo` (siempre al día, sin permisos).
- Ventanas de cada app, títulos, ventana con el foco: AX (`AXWindows`, `AXTitle`...).
- Id de una ventana: su número de ventana (`CGWindowID`) con `_AXUIElementGetWindow`, la
  misma función privada que usan yabai, Hammerspoon o AltTab; si falla, un id sintético.
- Activar: `AXRaise` en la ventana y `AXFrontmost` en su app. Desde macOS 14,
  `NSRunningApplication.activate` desde una app de fondo puede no hacer nada (activación
  cooperativa); `AXFrontmost` sí funciona con el permiso de Accesibilidad.

No se usa `NSWorkspace.frontmostApplication`: sin un bucle de eventos en el hilo principal
(modo `run`, `--probe`) no se actualiza.

Si la app no tiene ventana con el foco (p. ej. el escritorio del Finder), la "ventana" activa
es `-pid`: restaurarla vuelve a activar esa app.
"""

from __future__ import annotations

import ctypes
import functools
import logging
from typing import Any

from paste_photo.core.ports import WindowInfo

log = logging.getLogger(__name__)

APP_SERVICES = "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
AX_SUCCESS = 0


def synthetic_id(pid: int, index: int) -> int:
    """Id estable mientras la app no abra/cierre ventanas (si no hay número de ventana)."""
    return (pid << 8) | (index & 0xFF) | (1 << 40)


def is_trusted(prompt: bool = False) -> bool:
    """¿Tiene este proceso el permiso de Accesibilidad? `prompt` abre el aviso del sistema."""
    try:
        import ApplicationServices as ax
    except ImportError:
        return False
    if prompt:
        return bool(ax.AXIsProcessTrustedWithOptions({ax.kAXTrustedCheckOptionPrompt: True}))
    return bool(ax.AXIsProcessTrusted())


@functools.cache
def _get_window_fn():
    try:
        fn = ctypes.cdll.LoadLibrary(APP_SERVICES)._AXUIElementGetWindow
    except (OSError, AttributeError):
        log.debug("_AXUIElementGetWindow no disponible: ids de ventana sintéticos")
        return None
    fn.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
    fn.restype = ctypes.c_int32
    return fn


def _window_number(element: Any) -> int:
    fn = _get_window_fn()
    if fn is None:
        return 0
    import objc

    number = ctypes.c_uint32(0)
    if fn(ctypes.c_void_p(objc.pyobjc_id(element)), ctypes.byref(number)) == AX_SUCCESS:
        return int(number.value)
    return 0


class MacWindowSystem:
    """`WindowSystem` sobre AX. Recuerda el elemento AX de cada id del último listado."""

    def __init__(self) -> None:
        import ApplicationServices
        import objc
        import Quartz

        self._ax = ApplicationServices
        self._objc = objc
        self._quartz = Quartz
        self._elements: dict[int, tuple[int, Any]] = {}

    # --- WindowSystem ----------------------------------------------------------------

    def list_windows(self) -> list[WindowInfo]:
        with self._objc.autorelease_pool():
            found: list[WindowInfo] = []
            elements: dict[int, tuple[int, Any]] = {}
            for pid in self._pids_with_windows():
                app = self._ax.AXUIElementCreateApplication(pid)
                for index, window in enumerate(self._attr(app, "AXWindows") or []):
                    window_id = _window_number(window) or synthetic_id(pid, index)
                    title = self._attr(window, "AXTitle") or ""
                    found.append(WindowInfo(window_id, str(title), pid))
                    elements[window_id] = (pid, window)
            self._elements = elements
            return found

    def active_window(self) -> int | None:
        with self._objc.autorelease_pool():
            system = self._ax.AXUIElementCreateSystemWide()
            app = self._attr(system, "AXFocusedApplication")
            if app is None:
                return None
            err, pid = self._ax.AXUIElementGetPid(app, None)
            if err != AX_SUCCESS:
                return None
            window = self._attr(app, "AXFocusedWindow")
            if window is None:
                return -pid
            number = _window_number(window)
            if not number:
                return -pid
            self._elements[number] = (pid, window)
            return number

    def activate(self, window_id: int) -> None:
        with self._objc.autorelease_pool():
            if window_id < 0:
                self._activate_app(-window_id)
                return
            entry = self._elements.get(window_id)
            if entry is None:
                self.list_windows()
                entry = self._elements.get(window_id)
            if entry is None:
                raise RuntimeError(f"La ventana {window_id} ya no existe")
            pid, window = entry
            self._ax.AXUIElementPerformAction(window, "AXRaise")
            self._ax.AXUIElementSetAttributeValue(window, "AXMain", True)
            self._activate_app(pid)

    # --- helpers ---------------------------------------------------------------------

    def _attr(self, element: Any, name: str) -> Any:
        err, value = self._ax.AXUIElementCopyAttributeValue(element, name, None)
        return value if err == AX_SUCCESS else None

    def _pids_with_windows(self) -> list[int]:
        q = self._quartz
        options = q.kCGWindowListOptionAll | q.kCGWindowListExcludeDesktopElements
        pids: list[int] = []
        for info in q.CGWindowListCopyWindowInfo(options, q.kCGNullWindowID) or []:
            pid = int(info.get("kCGWindowOwnerPID", 0))
            if info.get("kCGWindowLayer", 0) == 0 and pid and pid not in pids:
                pids.append(pid)
        return pids

    def _activate_app(self, pid: int) -> None:
        app = self._ax.AXUIElementCreateApplication(pid)
        if self._ax.AXUIElementSetAttributeValue(app, "AXFrontmost", True) == AX_SUCCESS:
            return
        from AppKit import NSApplicationActivateIgnoringOtherApps, NSRunningApplication

        running = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
        if running is None or not running.activateWithOptions_(
                NSApplicationActivateIgnoringOtherApps):
            raise RuntimeError(f"No se pudo activar la app {pid}")


class MacFocus:
    """FocusManager (Memento: ventana activa, o `-pid` de la app activa sin ventana)."""

    def __init__(self, windows: MacWindowSystem | None) -> None:
        self._windows = windows

    def capture(self) -> int | None:
        if self._windows is None:
            return None
        try:
            return self._windows.active_window()
        except Exception:
            return None

    def restore(self, snapshot: int | None) -> None:
        if snapshot and self._windows is not None:
            try:
                self._windows.activate(snapshot)
            except Exception:
                log.debug("No se pudo devolver el foco a %s", snapshot, exc_info=True)

    def activate(self, window_id: int) -> None:
        if self._windows is None:
            raise RuntimeError("Sin acceso a las ventanas (falta pyobjc)")
        self._windows.activate(window_id)
