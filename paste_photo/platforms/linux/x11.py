# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""X11 (y apps XWayland): ventanas por EWMH y teclado por XTEST, con python-xlib.

Funciona con cualquier gestor de ventanas. Si el gestor no publica `_NET_CLIENT_LIST`
(gestores mínimos, el de WSLg), se recorre el árbol de ventanas; si una ventana no publica
`_NET_WM_PID`, se pide el PID a la extensión XRes del servidor.
"""

from __future__ import annotations

import logging
import threading
import time

from paste_photo.core.hotkey import parse_hotkey
from paste_photo.core.ports import WindowInfo

log = logging.getLogger(__name__)

MODIFIER_KEYSYMS = {"ctrl": "Control_L", "alt": "Alt_L", "shift": "Shift_L",
                    "win": "Super_L", "cmd": "Super_L"}
NAMED_KEYSYMS = {"enter": "Return", "tab": "Tab", "esc": "Escape", "space": "space",
                 "insert": "Insert"}


def keysym_names(hotkey: str) -> tuple[list[str], str]:
    """"ctrl+v" → (["Control_L"], "v"). Puro: se prueba sin X."""
    parsed = parse_hotkey(hotkey)
    return [MODIFIER_KEYSYMS[m] for m in parsed.modifiers], NAMED_KEYSYMS.get(parsed.key,
                                                                              parsed.key)


class _X:
    """Conexión perezosa y compartida (python-xlib no es thread-safe: se serializa)."""

    def __init__(self) -> None:
        self._display = None
        self.lock = threading.RLock()

    @property
    def display(self):
        if self._display is None:
            from Xlib import display

            self._display = display.Display()
            # Una ventana puede cerrarse mientras se consulta (BadWindow): no es un error de
            # la app; python-xlib lo imprimiría por stderr.
            self._display.set_error_handler(
                lambda error, request: log.debug("Error X ignorado: %s", error))
        return self._display

    def atom(self, name: str) -> int:
        return self.display.intern_atom(name)


class X11WindowSystem:
    def __init__(self, x: _X | None = None) -> None:
        self._x = x or _X()

    def list_windows(self) -> list[WindowInfo]:
        with self._x.lock:
            return [info for wid in self._client_ids() if (info := self._info(wid))]

    def active_window(self) -> int | None:
        from Xlib import X

        with self._x.lock:
            root = self._x.display.screen().root
            prop = root.get_full_property(self._x.atom("_NET_ACTIVE_WINDOW"), X.AnyPropertyType)
            if prop and prop.value and prop.value[0]:
                return int(prop.value[0])
            focus = self._x.display.get_input_focus().focus
            return int(focus.id) if hasattr(focus, "id") and focus.id > 1 else None

    def activate(self, window_id: int) -> None:
        from Xlib import X
        from Xlib.protocol import event

        with self._x.lock:
            d = self._x.display
            root = d.screen().root
            window = d.create_resource_object("window", window_id)
            # Petición estándar al gestor de ventanas (fuente 2 = "pager/herramienta").
            message = event.ClientMessage(window=window,
                                          client_type=self._x.atom("_NET_ACTIVE_WINDOW"),
                                          data=(32, [2, X.CurrentTime, 0, 0, 0]))
            root.send_event(message, event_mask=X.SubstructureRedirectMask
                            | X.SubstructureNotifyMask)
            window.configure(stack_mode=X.Above)
            try:  # con gestores que ignoran la petición, el foco X directo basta para XTEST
                window.set_input_focus(X.RevertToParent, X.CurrentTime)
            except Exception:
                pass
            d.sync()

    # --- helpers -----------------------------------------------------------

    def _client_ids(self) -> list[int]:
        from Xlib import X

        root = self._x.display.screen().root
        prop = root.get_full_property(self._x.atom("_NET_CLIENT_LIST"), X.AnyPropertyType)
        if prop is not None and len(prop.value):
            return [int(w) for w in prop.value]
        # Sin EWMH: ventanas de primer nivel visibles con título (y sus hijas directas, por
        # si el gestor las envuelve en un marco).
        ids = []
        for child in root.query_tree().children:
            try:
                if child.get_attributes().map_state != X.IsViewable:
                    continue
                ids.append(int(child.id))
                ids.extend(int(c.id) for c in child.query_tree().children)
            except Exception:
                continue
        return ids

    def _info(self, window_id: int) -> WindowInfo | None:
        from Xlib import X

        d = self._x.display
        try:
            window = d.create_resource_object("window", window_id)
            title = self._title(window)
            if not title:
                return None
            pid_prop = window.get_full_property(self._x.atom("_NET_WM_PID"), X.AnyPropertyType)
            pid = int(pid_prop.value[0]) if pid_prop and len(pid_prop.value) else self._xres_pid(
                window_id)
            wm_class = window.get_wm_class() or ("", "")
            return WindowInfo(window_id, title, pid or 0, wm_class[-1] or "")
        except Exception:
            return None

    def _title(self, window) -> str:
        prop = window.get_full_property(self._x.atom("_NET_WM_NAME"), self._x.atom("UTF8_STRING"))
        if prop is not None and prop.value:
            value = prop.value
            return value.decode("utf-8", "replace") if isinstance(value, bytes) else str(value)
        name = window.get_wm_name()
        if isinstance(name, bytes):
            return name.decode("latin-1", "replace")
        return name or ""

    def _xres_pid(self, window_id: int) -> int:
        """PID por la extensión XRes (sirve aunque el cliente no publique _NET_WM_PID)."""
        try:
            from Xlib.ext import res

            d = self._x.display
            if not d.has_extension("X-Resource"):
                return 0
            spec = [{"client": window_id, "mask": res.LocalClientPIDMask}]
            for client in d.res_query_client_ids(spec).ids:
                if client.value:
                    return int(client.value[0])
        except Exception:
            log.debug("XRes no disponible", exc_info=True)
        return 0


class X11Keyboard:
    """Cada pulsación abre su propia conexión X: una conexión de larga duración se queda con
    el mapa de teclado de cuando se abrió (no procesa MappingNotify) y, si el servidor lo
    cambia después (cambio de distribución, XWayland/WSLg), Ctrl deja de aplicarse."""

    def __init__(self, x: _X | None = None, key_delay_s: float = 0.02) -> None:
        self._delay = key_delay_s
        self._lock = threading.Lock()

    def send_hotkey(self, hotkey: str) -> None:
        from Xlib import XK, X, display
        from Xlib.ext import xtest

        modifiers, key = keysym_names(hotkey)
        with self._lock:
            d = display.Display()

            def code(name: str) -> int:
                keycode = d.keysym_to_keycode(XK.string_to_keysym(name))
                if not keycode:
                    raise ValueError(f"Tecla sin código en este teclado: {name}")
                return keycode

            mod_codes = [code(m) for m in modifiers]
            key_code = code(key)
            events = ([(X.KeyPress, c) for c in mod_codes]
                      + [(X.KeyPress, key_code), (X.KeyRelease, key_code)]
                      + [(X.KeyRelease, c) for c in reversed(mod_codes)])
            # Un evento cada vez, sincronizado y con pausa (como xdotool): en XWayland XTEST
            # pasa por libei y, si se envían de golpe, el Ctrl puede soltarse antes que la V.
            try:
                for kind, keycode in events:
                    xtest.fake_input(d, kind, keycode)
                    d.sync()
                    time.sleep(self._delay)
            finally:
                d.close()
