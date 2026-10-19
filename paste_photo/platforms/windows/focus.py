"""Gestión del foco de ventanas en Windows."""

from __future__ import annotations

import logging

import win32api
import win32con
import win32gui

log = logging.getLogger(__name__)


class WindowsFocusManager:
    def capture(self) -> int:
        return win32gui.GetForegroundWindow()

    def restore(self, snapshot: int) -> None:
        if snapshot and win32gui.IsWindow(snapshot):
            self.activate(snapshot)

    def activate(self, window_id: int) -> None:
        if win32gui.IsIconic(window_id):
            win32gui.ShowWindow(window_id, win32con.SW_RESTORE)
        # Windows solo deja robar el foco al proceso que recibió la última entrada.
        # Una pulsación sintética de Alt nos concede ese permiso.
        win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
        try:
            win32gui.SetForegroundWindow(window_id)
        except win32gui.error:
            log.warning("No se pudo activar la ventana %s", window_id)
        finally:
            win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
