"""Adaptadores de Windows (pywin32)."""

from __future__ import annotations

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
