# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Base para destinos de Windows con pestañas visibles por UI Automation (Template Method).

Las subclases deciden *qué ventanas* mirar, *cómo puntuar* cada pestaña y, opcionalmente,
qué comprobar/hacer con la pestaña ya visible (`_before_paste`, p. ej. enfocar el prompt).
Lo común: localizar candidatos, ordenarlos, enfocar, pegar y restaurar las pestañas.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any

from paste_photo.core.ports import TargetHandle
from paste_photo.targets.registry import TargetContext

log = logging.getLogger(__name__)


class TabNotReady(Exception):
    """La pestaña candidata no sirve (p. ej. no tiene prompt): probar la siguiente."""


def safe_attr(ctrl: Any, attr: str) -> Any:
    """Lee una propiedad UIA tolerando elementos que desaparecen (COMError)."""
    try:
        return getattr(ctrl, attr) or ""
    except Exception:
        return ""


class UiaTabTarget:
    name = "uia_tab"
    tab_search_depth = 12

    def __init__(
        self,
        ctx: TargetContext,
        *,
        title_regex: str,
        paste_keys: str,
        settle_ms: int = 150,
        restore_tab: bool = True,
    ) -> None:
        # Imports perezosos: el módulo se importa en cualquier SO para registrarse.
        import uiautomation
        import win32gui
        import win32process

        self._auto = uiautomation
        self._win32gui = win32gui
        self._win32process = win32process
        self._ctx = ctx
        self._title_re = re.compile(title_regex)
        self._paste_keys = paste_keys
        self._settle_s = settle_ms / 1000
        self._restore_tab = restore_tab

    # --- puntos de extensión ----------------------------------------------

    def _candidate_windows(self) -> list[int]:
        raise NotImplementedError

    def _rank(self, hwnd: int, tab: Any, selected: bool) -> int | None:
        """Puntuación de una pestaña: None = no es Claude; menor = mejor."""
        return 1 if self._title_re.search(safe_attr(tab, "Name")) else None

    def _before_paste(self, handle: TargetHandle) -> None:
        """Con la pestaña ya visible y enfocada. Lanza `TabNotReady` para descartarla."""

    # --- TargetStrategy ----------------------------------------------------

    def locate(self) -> TargetHandle | None:
        recency = self._ctx.recency
        scored: list[tuple[tuple[float, int, bool, int], TargetHandle]] = []
        for hwnd in self._candidate_windows():
            for tab in self._tabs(hwnd):
                selected = self._is_selected(tab)
                rank = self._rank(hwnd, tab, selected)
                if rank is None:
                    continue
                label = safe_attr(tab, "Name")
                handle = TargetHandle(window_id=hwnd, label=label, extra={"tab": tab})
                # Prioridad: ventana usada más recientemente > puntuación (URL antes que
                # título) > pestaña seleccionada en ella > orden.
                key = (-recency.last_seen(hwnd), rank, not selected, len(scored))
                scored.append((key, handle))
        if not scored:
            return None
        scored.sort(key=lambda item: item[0])
        candidates = [handle for _key, handle in scored]
        if len(candidates) > 1:
            log.debug("%s: candidatos %s", self.name, [c.label for c in candidates])
        best = candidates[0]
        return TargetHandle(best.window_id, best.label, {**best.extra, "candidates": candidates})

    def paste(self, handle: TargetHandle) -> None:
        candidates: list[TargetHandle] = handle.extra.get("candidates", [handle])
        previous: dict[int, Any] = {}
        try:
            for candidate in candidates:
                if self._restore_tab and candidate.window_id not in previous:
                    previous[candidate.window_id] = self._selected_tab(candidate.window_id)
                self._show(candidate)
                try:
                    self._before_paste(candidate)
                except TabNotReady as reason:
                    log.info("%s: descartada %r (%s)", self.name, candidate.label, reason)
                    continue
                self._ctx.keyboard.send_hotkey(self._paste_keys)
                time.sleep(self._settle_s)
                if candidate is not candidates[0]:
                    log.info("%s: pegado en %r", self.name, candidate.label)
                return
            raise RuntimeError(f"{self.name}: ningún candidato estaba listo para pegar")
        finally:
            for tab in previous.values():
                if tab is not None and not self._is_selected(tab):
                    tab.GetSelectionItemPattern().Select()

    # --- helpers -----------------------------------------------------------

    def _show(self, handle: TargetHandle) -> None:
        tab = handle.extra["tab"]
        self._ctx.focus.activate(handle.window_id)
        if not self._is_selected(tab):
            tab.GetSelectionItemPattern().Select()
        time.sleep(self._settle_s)

    def _windows_of_class(self, *classes: str) -> list[int]:
        found: list[int] = []

        def collect(hwnd: int, _: Any) -> None:
            if self._win32gui.GetClassName(hwnd) in classes and self._win32gui.IsWindowVisible(
                hwnd
            ):
                found.append(hwnd)

        self._win32gui.EnumWindows(collect, None)
        return found

    def _window_pid(self, hwnd: int) -> int:
        return self._win32process.GetWindowThreadProcessId(hwnd)[1]

    def _walk(self, hwnd: int, max_depth: int) -> list[Any]:
        """Elementos UIA de la ventana; si el árbol cambia a mitad, devuelve lo leído."""
        root = self._auto.ControlFromHandle(hwnd)
        found: list[Any] = []
        if root is None:
            return found
        try:
            for ctrl, _depth in self._auto.WalkControl(root, maxDepth=max_depth):
                found.append(ctrl)
        except Exception:
            log.debug("Árbol UIA de %s cambió durante el recorrido", hwnd)
        return found

    def _tabs(self, hwnd: int) -> list[Any]:
        tab_type = self._auto.ControlType.TabItemControl
        controls = self._walk(hwnd, self.tab_search_depth)
        return [c for c in controls if safe_attr(c, "ControlType") == tab_type]

    def _selected_tab(self, hwnd: int) -> Any | None:
        return next((t for t in self._tabs(hwnd) if self._is_selected(t)), None)

    @staticmethod
    def _is_selected(tab: Any) -> bool:
        try:
            return bool(tab.GetSelectionItemPattern().IsSelected)
        except Exception:
            return False
