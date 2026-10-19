# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Detecta capturas escuchando cambios de imagen en el portapapeles (Win+Shift+S)."""

from __future__ import annotations

import ctypes
import hashlib
import logging
import threading
import time
from collections.abc import Callable

import win32clipboard
import win32con
import win32gui

from paste_photo.core.events import ScreenshotCaptured
from paste_photo.imaging import cached, dib_to_png

log = logging.getLogger(__name__)

WM_CLIPBOARDUPDATE = 0x031D
_CLASS_NAME = "PastePhotoClipboardListener"


class WindowsClipboardSource:
    """Ventana oculta de solo mensajes registrada con `AddClipboardFormatListener`.

    El bucle de mensajes corre en un hilo propio; `on_capture` se invoca desde él.
    """

    def __init__(self, open_retries: int = 10, retry_delay_s: float = 0.05) -> None:
        self._open_retries = open_retries
        self._retry_delay_s = retry_delay_s
        self._on_capture: Callable[[ScreenshotCaptured], None] | None = None
        self._hwnd: int | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()

    def start(self, on_capture: Callable[[ScreenshotCaptured], None]) -> None:
        self._on_capture = on_capture
        self._thread = threading.Thread(target=self._run, name="clipboard-listener", daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=5):
            raise RuntimeError("No se pudo iniciar el listener del portapapeles")

    def stop(self) -> None:
        if self._hwnd:
            win32gui.PostMessage(self._hwnd, win32con.WM_CLOSE, 0, 0)
        if self._thread:
            self._thread.join(timeout=2)

    def _run(self) -> None:
        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = self._wnd_proc
        wc.lpszClassName = _CLASS_NAME
        wc.hInstance = win32gui.GetModuleHandle(None)
        try:
            win32gui.RegisterClass(wc)
        except win32gui.error:
            pass  # ya registrada en este proceso
        self._hwnd = win32gui.CreateWindow(
            _CLASS_NAME, _CLASS_NAME, 0, 0, 0, 0, 0, win32con.HWND_MESSAGE, 0, wc.hInstance, None
        )
        if not ctypes.windll.user32.AddClipboardFormatListener(self._hwnd):
            raise ctypes.WinError()
        log.debug("Escuchando el portapapeles (hwnd=%s)", self._hwnd)
        self._ready.set()
        win32gui.PumpMessages()

    def _wnd_proc(self, hwnd: int, msg: int, wparam: int, lparam: int) -> int:
        if msg == WM_CLIPBOARDUPDATE:
            self._on_clipboard_update()
            return 0
        if msg == win32con.WM_CLOSE:
            ctypes.windll.user32.RemoveClipboardFormatListener(hwnd)
            win32gui.DestroyWindow(hwnd)
            return 0
        if msg == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
            return 0
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def _on_clipboard_update(self) -> None:
        data = self._read_image()
        if data is None or self._on_capture is None:
            return
        event = ScreenshotCaptured(
            image_hash=hashlib.sha1(data).hexdigest(),
            timestamp=time.monotonic(),
            load_png=cached(lambda: dib_to_png(data)),
        )
        self._on_capture(event)

    def _read_image(self) -> bytes | None:
        # Otro proceso puede tener el portapapeles abierto justo ahora: reintentar.
        for _ in range(self._open_retries):
            try:
                win32clipboard.OpenClipboard()
            except win32clipboard.error:
                time.sleep(self._retry_delay_s)
                continue
            try:
                if not win32clipboard.IsClipboardFormatAvailable(win32con.CF_DIB):
                    return None
                return win32clipboard.GetClipboardData(win32con.CF_DIB)
            finally:
                win32clipboard.CloseClipboard()
        log.warning("No se pudo abrir el portapapeles")
        return None
