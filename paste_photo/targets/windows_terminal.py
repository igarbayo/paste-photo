"""Claude Code CLI dentro de una pestaña de Windows Terminal."""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Mapping
from typing import Any

from paste_photo.core.ports import TargetHandle
from paste_photo.targets.registry import TargetContext, register_target

log = logging.getLogger(__name__)

WT_WINDOW_CLASS = "CASCADIA_HOSTING_WINDOW_CLASS"
# Claude Code pone en el título un glifo de estado: ✳ en reposo, ◐◓◑◒ trabajando.
DEFAULT_TITLE_REGEX = r"^[✳✻✽✶✢·◐◓◑◒]\s|Claude Code"
DEFAULT_PASTE_KEYS = "alt+v"  # Ctrl+V en Windows Terminal solo pega texto


class WindowsTerminalTarget:
    name = "windows_terminal"

    def __init__(
        self,
        ctx: TargetContext,
        *,
        title_regex: str = DEFAULT_TITLE_REGEX,
        paste_keys: str = DEFAULT_PASTE_KEYS,
        settle_ms: int = 150,
        restore_tab: bool = True,
    ) -> None:
        # Imports perezosos: este módulo se importa en cualquier SO para registrarse.
        import uiautomation
        import win32gui

        self._auto = uiautomation
        self._win32gui = win32gui
        self._ctx = ctx
        self._title_re = re.compile(title_regex)
        self._paste_keys = paste_keys
        self._settle_s = settle_ms / 1000
        self._restore_tab = restore_tab

    def locate(self) -> TargetHandle | None:
        matches: list[TargetHandle] = []
        for hwnd in self._terminal_windows():
            for tab in self._tabs(hwnd):
                if self._title_re.search(tab.Name):
                    matches.append(TargetHandle(window_id=hwnd, label=tab.Name, extra={"tab": tab}))
        if not matches:
            return None
        if len(matches) > 1:
            log.info("Hay %d pestañas de Claude Code; se usa la más visible", len(matches))
        # Prioridad: pestaña seleccionada > en la ventana activa > la primera.
        foreground = self._win32gui.GetForegroundWindow()
        matches.sort(
            key=lambda h: (not self._is_selected(h.extra["tab"]), h.window_id != foreground)
        )
        return matches[0]

    def paste(self, handle: TargetHandle) -> None:
        tab = handle.extra["tab"]
        previous_tab = self._selected_tab(handle.window_id) if self._restore_tab else None

        self._ctx.focus.activate(handle.window_id)
        if not self._is_selected(tab):
            tab.GetSelectionItemPattern().Select()
        time.sleep(self._settle_s)
        self._ctx.keyboard.send_hotkey(self._paste_keys)
        time.sleep(self._settle_s)

        if previous_tab is not None and previous_tab.Name != tab.Name:
            previous_tab.GetSelectionItemPattern().Select()

    # --- helpers -----------------------------------------------------------

    def _terminal_windows(self) -> list[int]:
        found: list[int] = []

        def collect(hwnd: int, _: Any) -> None:
            if self._win32gui.GetClassName(hwnd) == WT_WINDOW_CLASS:
                found.append(hwnd)

        self._win32gui.EnumWindows(collect, None)
        return found

    def _tabs(self, hwnd: int) -> list[Any]:
        root = self._auto.ControlFromHandle(hwnd)
        if root is None:
            return []
        return [
            ctrl
            for ctrl, _depth in self._auto.WalkControl(root, maxDepth=8)
            if ctrl.ControlType == self._auto.ControlType.TabItemControl
        ]

    def _selected_tab(self, hwnd: int) -> Any | None:
        return next((t for t in self._tabs(hwnd) if self._is_selected(t)), None)

    @staticmethod
    def _is_selected(tab: Any) -> bool:
        try:
            return bool(tab.GetSelectionItemPattern().IsSelected)
        except Exception:
            return False


@register_target("windows_terminal")
def build(options: Mapping[str, Any], ctx: TargetContext) -> WindowsTerminalTarget:
    if ctx.platform != "windows":
        raise ValueError("El destino windows_terminal solo funciona en Windows")
    return WindowsTerminalTarget(
        ctx,
        title_regex=options.get("title_regex", DEFAULT_TITLE_REGEX),
        paste_keys=options.get("paste_keys", DEFAULT_PASTE_KEYS),
        settle_ms=int(options.get("settle_ms", 150)),
        restore_tab=bool(options.get("restore_tab", True)),
    )
