# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Adaptadores de Windows (pywin32)."""

from __future__ import annotations

from contextlib import AbstractContextManager

from paste_photo.platforms.windows.autostart import WindowsAutostart
from paste_photo.platforms.windows.clipboard_source import WindowsClipboardSource
from paste_photo.platforms.windows.focus import WindowsFocusManager
from paste_photo.platforms.windows.keyboard import WindowsKeyboard


class WindowsFactory:
    name = "windows"

    def create_screenshot_source(self) -> WindowsClipboardSource:
        return WindowsClipboardSource()

    def create_focus_manager(self) -> WindowsFocusManager:
        return WindowsFocusManager()

    def create_keyboard(self) -> WindowsKeyboard:
        return WindowsKeyboard()

    def create_autostart(self) -> WindowsAutostart:
        return WindowsAutostart()

    def create_window_system(self) -> None:
        return None  # los destinos de Windows usan UI Automation directamente

    def worker_context(self) -> AbstractContextManager[None]:
        # UI Automation usa COM: cada hilo que lo use debe inicializarlo.
        import uiautomation

        return uiautomation.UIAutomationInitializerInThread()
