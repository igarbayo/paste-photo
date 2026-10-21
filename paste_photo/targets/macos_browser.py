# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""claude.ai en un navegador de macOS sin la extensión: pestaña → foco → Cmd+V.

- **Safari y los Chromium con AppleScript** (Chrome, Edge, Brave, Vivaldi, Chromium): AppleScript
  da la URL y el título de **todas** las pestañas, así que se encuentra claude.ai aunque esté en
  una pestaña de fondo; se selecciona, se pulsa Cmd+V y se vuelve a la pestaña que había.
- **Resto** (Firefox, LibreWolf, Zen, Arc, Opera... o si se deniega la Automatización): como
  `linux_browser`, por el título de la ventana; solo si la pestaña de Claude es la activa.

Al volver a la pestaña, el navegador devuelve el foco al elemento que lo tenía: la imagen va al
cursor del prompt si estaba en él. Safari no admite la extensión de PastePhoto (sería una
Safari Web Extension con app propia): este destino es su única vía.
"""

from __future__ import annotations

import logging
import re
import subprocess
import time
from collections.abc import Mapping
from typing import Any

from paste_photo.core.events import ScreenshotCaptured
from paste_photo.core.ports import TargetHandle, WindowInfo
from paste_photo.targets._applescript import osascript, parse_rows
from paste_photo.targets._processes import process_name, processes_named
from paste_photo.targets.browser import (
    DEFAULT_CHAT_URL_REGEX,
    DEFAULT_TITLE_REGEX,
    DEFAULT_URL_REGEX,
)
from paste_photo.targets.registry import TargetContext, register_target

log = logging.getLogger(__name__)

DEFAULT_PASTE_KEYS = "cmd+v"
# Proceso principal (psutil, en minúsculas) → (bundle id, dialecto de AppleScript).
SCRIPTABLE_BROWSERS = {
    "safari": ("com.apple.Safari", "safari"),
    "google chrome": ("com.google.Chrome", "chromium"),
    "microsoft edge": ("com.microsoft.edgemac", "chromium"),
    "brave browser": ("com.brave.Browser", "chromium"),
    "vivaldi": ("com.vivaldi.Vivaldi", "chromium"),
    "chromium": ("org.chromium.Chromium", "chromium"),
}
# Navegadores sin AppleScript de pestañas: se usa el título de su ventana.
DEFAULT_BROWSERS = ("firefox", "librewolf", "zen", "waterfox", "floorp", "arc", "opera",
                    "orion")

# Dentro de `tell`, `tab` es la clase "pestaña": los separadores se crean fuera.
_HEADER = """
on run argv
    set sep to character id 9
    set nl to character id 10
    set out to ""
"""
_TAB_FIELDS = {"chromium": ("active tab index of w", "title of t"),
               "safari": ("index of current tab of w", "name of t")}
LIST_SCRIPT = _HEADER + """
    tell application id "{bundle}"
        repeat with w in windows
            try
                set active to {active}
                set i to 0
                repeat with t in tabs of w
                    set i to i + 1
                    set u to URL of t
                    if u is missing value then set u to ""
                    set n to {title}
                    if n is missing value then set n to ""
                    set row to (id of w as text) & sep & i & sep & (i = active)
                    set out to out & row & sep & u & sep & n & nl
                end repeat
            end try
        end repeat
    end tell
    return out
end run
"""
_SELECT = {"chromium": ("active tab index of w", "set active tab index of w to ti"),
           "safari": ("index of current tab of w", "set current tab of w to tab ti of w")}
SELECT_SCRIPT = """
on run argv
    set wid to (item 1 of argv) as integer
    set ti to (item 2 of argv) as integer
    tell application id "{bundle}"
        set w to window id wid
        set previous to {current}
        {select}
        if item 3 of argv is "front" then
            set index of w to 1
            activate
        end if
        return previous as text
    end tell
end run
"""


def list_script(bundle: str, dialect: str) -> str:
    active, title = _TAB_FIELDS[dialect]
    return LIST_SCRIPT.replace("{bundle}", bundle).replace("{active}", active).replace(
        "{title}", title)


def select_script(bundle: str, dialect: str) -> str:
    current, select = _SELECT[dialect]
    return SELECT_SCRIPT.replace("{bundle}", bundle).replace("{current}", current).replace(
        "{select}", select)


class MacBrowserTarget:
    name = "macos_browser"

    def __init__(self, ctx: TargetContext, *, url_regex: str = DEFAULT_URL_REGEX,
                 chat_url_regex: str = DEFAULT_CHAT_URL_REGEX,
                 title_regex: str = DEFAULT_TITLE_REGEX,
                 browsers: tuple[str, ...] = DEFAULT_BROWSERS, scriptable: bool = True,
                 paste_keys: str = DEFAULT_PASTE_KEYS, settle_ms: int = 250,
                 restore_tab: bool = True) -> None:
        self._ctx = ctx
        self._url_re = re.compile(url_regex)
        self._chat_re = re.compile(chat_url_regex)
        self._title_re = re.compile(title_regex)
        self._browsers = {b.lower() for b in browsers}
        self._scriptable = scriptable
        self._paste_keys = paste_keys
        self._settle_s = settle_ms / 1000
        self._restore_tab = restore_tab

    # --- TargetStrategy ----------------------------------------------------------------

    def locate(self) -> TargetHandle | None:
        windows = self._list_windows()
        scored: list[tuple[tuple[float, int, bool, int], TargetHandle]] = []
        by_window = set(self._browsers)
        if self._scriptable:
            running = {(p.info["name"] or "").lower(): p.pid
                       for p in processes_named(SCRIPTABLE_BROWSERS)}
            for name, pid in running.items():
                try:
                    tabs = self._scripted_tabs(name)
                except (OSError, RuntimeError, subprocess.SubprocessError) as error:
                    log.debug("%s: sin AppleScript (%s); se usa su ventana", name, error)
                    by_window.add(name)
                    continue
                own = [w for w in windows if w.pid == pid]
                for window, index, active, url, title in tabs:
                    if self._url_re.search(url):
                        rank = 0 if self._chat_re.search(url) else None  # p. ej. un artifact
                    else:
                        rank = 1 if self._title_re.search(title) else None
                    if rank is None:
                        continue
                    window_id = self._os_window(own, tabs, window)
                    handle = TargetHandle(window_id, title or url, {
                        "browser": name, "window": window, "tab": index})
                    key = (-self._ctx.recency.last_seen(window_id), rank, not active, len(scored))
                    scored.append((key, handle))
        for window in windows:
            if self._title_re.search(window.title) and process_name(window.pid) in by_window:
                key = (-self._ctx.recency.last_seen(window.id), 1, False, len(scored))
                scored.append((key, TargetHandle(window.id, window.title, {"pid": window.pid})))
        if not scored:
            return None
        scored.sort(key=lambda item: item[0])
        candidates = [handle for _key, handle in scored]
        best = candidates[0]
        return TargetHandle(best.window_id, best.label, {**best.extra, "candidates": candidates})

    def paste(self, handle: TargetHandle, shot: ScreenshotCaptured | None = None) -> None:
        errors = []
        for candidate in handle.extra.get("candidates", [handle]):
            try:
                if "browser" in candidate.extra:
                    self._paste_in_tab(candidate)
                else:
                    self._paste_in_window(candidate)
                return
            except (OSError, RuntimeError, subprocess.SubprocessError) as error:
                log.info("%s: no se pudo pegar en %r: %s", self.name, candidate.label, error)
                errors.append(str(error))
        raise RuntimeError(f"{self.name}: " + "; ".join(errors))

    # --- helpers -------------------------------------------------------------------------

    def _scripted_tabs(self, name: str) -> list[tuple[str, str, bool, str, str]]:
        bundle, dialect = SCRIPTABLE_BROWSERS[name]
        rows = parse_rows(osascript(list_script(bundle, dialect)), 5)
        return [(w, i, active == "true", url, title) for w, i, active, url, title in rows]

    def _os_window(self, own: list[WindowInfo], tabs: list, window: str) -> int:
        """Ventana del SO (para la prioridad por uso reciente) de una ventana de AppleScript:
        la que lleva el título de su pestaña activa; si no, la del navegador usada más
        recientemente."""
        active = next((t for w, _i, a, _u, t in tabs if w == window and a), None)
        if active:
            for candidate in own:
                if candidate.title.startswith(active):
                    return candidate.id
        best = max(own, key=lambda w: self._ctx.recency.last_seen(w.id), default=None)
        return best.id if best else 0

    def _paste_in_tab(self, handle: TargetHandle) -> None:
        bundle, dialect = SCRIPTABLE_BROWSERS[handle.extra["browser"]]
        script = select_script(bundle, dialect)
        window, tab = handle.extra["window"], handle.extra["tab"]
        previous = osascript(script, window, tab, "front").strip()
        time.sleep(self._settle_s)
        self._ctx.keyboard.send_hotkey(self._paste_keys)
        time.sleep(self._settle_s)
        if self._restore_tab and previous and previous != tab:
            try:
                osascript(script, window, previous, "back")
            except (OSError, RuntimeError, subprocess.SubprocessError) as error:
                log.debug("No se pudo volver a la pestaña anterior: %s", error)

    def _paste_in_window(self, handle: TargetHandle) -> None:
        if self._ctx.windows is None:
            raise RuntimeError("sin acceso a las ventanas (permiso de Accesibilidad)")
        self._ctx.windows.activate(handle.window_id)
        time.sleep(self._settle_s)
        self._ctx.keyboard.send_hotkey(self._paste_keys)
        time.sleep(self._settle_s)

    def _list_windows(self) -> list[WindowInfo]:
        if self._ctx.windows is None:
            return []
        try:
            return self._ctx.windows.list_windows()
        except Exception:
            log.debug("No se pudieron listar ventanas", exc_info=True)
            return []


@register_target("macos_browser", platforms=("macos",))
def build(options: Mapping[str, Any], ctx: TargetContext) -> MacBrowserTarget:
    return MacBrowserTarget(
        ctx,
        url_regex=options.get("url_regex", DEFAULT_URL_REGEX),
        chat_url_regex=options.get("chat_url_regex", DEFAULT_CHAT_URL_REGEX),
        title_regex=options.get("title_regex", DEFAULT_TITLE_REGEX),
        browsers=tuple(options.get("browsers", DEFAULT_BROWSERS)),
        scriptable=bool(options.get("scriptable", True)),
        paste_keys=options.get("paste_keys", DEFAULT_PASTE_KEYS),
        settle_ms=int(options.get("settle_ms", 250)),
        restore_tab=bool(options.get("restore_tab", True)),
    )
