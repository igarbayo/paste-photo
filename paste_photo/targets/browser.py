# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Cualquier chat de Claude en la web (claude.ai: Chat, Code, Design...) en un navegador.

Soportados en Windows: Chrome, Edge y demás navegadores Chromium.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from typing import Any

from paste_photo.core.ports import TargetHandle
from paste_photo.targets.registry import TargetContext, register_target

log = logging.getLogger(__name__)

# Coincidencia fuerte: URL de la pestaña visible (UI Automation solo da la URL de esa).
DEFAULT_URL_REGEX = r"^(?:https?://)?(?:[\w-]+\.)*claude\.ai(?:[/?#]|$)"
# Coincidencia débil, para pestañas en segundo plano: "<conversación> - Claude",
# "Claude Code", "Claude Design"... El navegador añade texto al nombre accesible
# ("Uso de memoria de ...: 345 MB", ": parte del grupo ...", " - Uso de memoria - ..."),
# por eso se busca la palabra suelta seguida de fin, separador o decoración.
# Los proyectos de Design se titulan con su nombre: solo se detectan visibles (por URL).
DEFAULT_TITLE_REGEX = r"(?:^|\s)Claude(?:\s(?:Code|Design))?(?=$|[:(]|\s[-–|]\s|\s\()"
DEFAULT_PASTE_KEYS = "ctrl+v"
DEFAULT_BROWSERS = ("chrome.exe", "msedge.exe", "brave.exe", "vivaldi.exe", "opera.exe")
# El prompt de claude.ai es un editor ProseMirror en Chat, Code y Design; su clase CSS llega
# a UI Automation como ClassName y no depende del idioma (el aria-label sí). Se compara como
# token exacto: hay contenedores con clases tipo "[&_.ProseMirror]:...".
DEFAULT_EDITOR_CLASS = "ProseMirror"
CHROMIUM_WINDOW_CLASS = "Chrome_WidgetWin_1"
OMNIBOX_CLASS = "OmniboxViewViews"

RANK_URL, RANK_TITLE = 0, 1


def _windows_browser_target():
    # La clase base importa pywin32/uiautomation: solo se carga en Windows.
    from paste_photo.targets._processes import process_name
    from paste_photo.targets._win_uia import TabNotReady, UiaTabTarget, safe_attr

    class WindowsBrowserTarget(UiaTabTarget):
        name = "browser"

        def __init__(
            self,
            ctx: TargetContext,
            *,
            url_regex: str = DEFAULT_URL_REGEX,
            browsers: tuple[str, ...] = DEFAULT_BROWSERS,
            editor_class: str = DEFAULT_EDITOR_CLASS,
            editor_search_depth: int = 45,
            **kwargs: Any,
        ) -> None:
            super().__init__(ctx, **kwargs)
            self._url_re = re.compile(url_regex, re.IGNORECASE)
            self._browsers = {b.lower() for b in browsers}
            self._editor_class = editor_class
            self._editor_depth = editor_search_depth

        def _candidate_windows(self) -> list[int]:
            return [
                w
                for w in self._windows_of_class(CHROMIUM_WINDOW_CLASS)
                if self._win32gui.GetWindowText(w)
                and process_name(self._window_pid(w)) in self._browsers
            ]

        def _rank(self, hwnd: int, tab: Any, selected: bool) -> int | None:
            if selected and self._url_re.search(self._visible_url(hwnd)):
                return RANK_URL
            return RANK_TITLE if self._title_re.search(safe_attr(tab, "Name")) else None

        def _before_paste(self, handle: TargetHandle) -> None:
            # Al cambiar de pestaña el foco no suele quedar en el prompt: lo ponemos.
            # UI Automation solo ve el contenido de la pestaña activa, por eso va aquí.
            editor = self._find_editor(handle.window_id)
            if editor is None:
                raise TabNotReady("no tiene prompt de Claude")
            editor.SetFocus()

        def _visible_url(self, hwnd: int) -> str:
            root = self._auto.ControlFromHandle(hwnd)
            omnibox = root.EditControl(searchDepth=12, ClassName=OMNIBOX_CLASS) if root else None
            if omnibox is None or not omnibox.Exists(0, 0):
                return ""
            try:
                return omnibox.GetValuePattern().Value or ""
            except Exception:
                return ""

        def _find_editor(self, hwnd: int) -> Any | None:
            # Se recorre la ventana entera: Chrome tiene varios DocumentControl (paneles
            # internos) y el primero no es la página.
            edit_type = self._auto.ControlType.EditControl
            for ctrl in self._walk(hwnd, self._editor_depth):
                if (
                    safe_attr(ctrl, "ControlType") == edit_type
                    and self._editor_class in safe_attr(ctrl, "ClassName").split()
                ):
                    return ctrl
            return None

    return WindowsBrowserTarget


@register_target("browser")
def build(options: Mapping[str, Any], ctx: TargetContext):
    if ctx.platform != "windows":
        raise NotImplementedError(
            "El destino browser solo está implementado en Windows. "
            "Receta en paste_photo/targets/CLAUDE.md."
        )
    return _windows_browser_target()(
        ctx,
        title_regex=options.get("title_regex", DEFAULT_TITLE_REGEX),
        url_regex=options.get("url_regex", DEFAULT_URL_REGEX),
        paste_keys=options.get("paste_keys", DEFAULT_PASTE_KEYS),
        settle_ms=int(options.get("settle_ms", 250)),
        restore_tab=bool(options.get("restore_tab", True)),
        browsers=tuple(options.get("browsers", DEFAULT_BROWSERS)),
        editor_class=options.get("editor_class", DEFAULT_EDITOR_CLASS),
    )
