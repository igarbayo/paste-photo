"""Abstract Factory: cada SO crea su familia coherente de adaptadores."""

from __future__ import annotations

import sys
from typing import Protocol

from paste_photo.core.ports import FocusManager, Keyboard, ScreenshotSource


class PlatformFactory(Protocol):
    name: str  # "windows" | "macos" | "linux"

    def create_screenshot_source(self) -> ScreenshotSource: ...

    def create_focus_manager(self) -> FocusManager: ...

    def create_keyboard(self) -> Keyboard: ...


def current_platform_name() -> str:
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def get_platform_factory(name: str | None = None) -> PlatformFactory:
    # Imports perezosos: cada módulo solo carga las librerías de su SO.
    name = name or current_platform_name()
    if name == "windows":
        from paste_photo.platforms.windows import WindowsFactory

        return WindowsFactory()
    if name == "macos":
        from paste_photo.platforms.macos import MacOSFactory

        return MacOSFactory()
    if name == "linux":
        from paste_photo.platforms.linux import LinuxFactory

        return LinuxFactory()
    raise ValueError(f"Plataforma desconocida: {name}")
