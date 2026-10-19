# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Gestión del foco de ventanas en Windows."""

from __future__ import annotations

import logging

import win32api
import win32con
import win32gui
import win32process

log = logging.getLogger(__name__)

# Tecla virtual sin asignar: concede permiso de foco sin efectos visibles.
# (Un Alt suelto abriría la barra de menús en navegadores y apps de escritorio.)
_VK_UNASSIGNED = 0xE8


class WindowsFocusManager:
    def capture(self) -> int:
        return win32gui.GetForegroundWindow()

    def restore(self, snapshot: int) -> None:
        if snapshot and win32gui.IsWindow(snapshot):
            self.activate(snapshot)

    def activate(self, window_id: int) -> None:
        if win32gui.IsIconic(window_id):
            win32gui.ShowWindow(window_id, win32con.SW_RESTORE)
        if self._try_attached(window_id):
            return
        # Windows solo deja robar el foco a quien recibió la última entrada:
        # una pulsación sintética de una tecla sin asignar nos concede ese permiso.
        win32api.keybd_event(_VK_UNASSIGNED, 0, 0, 0)
        win32api.keybd_event(_VK_UNASSIGNED, 0, win32con.KEYEVENTF_KEYUP, 0)
        if not self._set_foreground(window_id):
            log.warning("No se pudo activar la ventana %s", window_id)

    def _try_attached(self, window_id: int) -> bool:
        """Se une a la cola de entrada de la ventana activa para heredar su permiso."""
        foreground = win32gui.GetForegroundWindow()
        if foreground == window_id:
            return True
        fg_thread = win32process.GetWindowThreadProcessId(foreground)[0] if foreground else 0
        own_thread = win32api.GetCurrentThreadId()
        attached = bool(fg_thread) and fg_thread != own_thread
        if attached:
            attached = _attach(own_thread, fg_thread, True)
        try:
            return self._set_foreground(window_id)
        finally:
            if attached:
                _attach(own_thread, fg_thread, False)

    @staticmethod
    def _set_foreground(window_id: int) -> bool:
        try:
            win32gui.BringWindowToTop(window_id)
            win32gui.SetForegroundWindow(window_id)
        except win32gui.error:
            pass
        return win32gui.GetForegroundWindow() == window_id


def _attach(own_thread: int, other_thread: int, attach: bool) -> bool:
    try:
        win32process.AttachThreadInput(own_thread, other_thread, attach)
        return True
    except win32process.error:
        return False
