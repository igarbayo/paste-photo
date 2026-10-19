# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""KDE Plasma Wayland: ventanas con scripts de KWin y teclado con el portal RemoteDesktop.

- Ventanas: se carga por D-Bus un script de KWin de un solo uso que lista (o activa)
  ventanas y devuelve el resultado llamando por D-Bus a este proceso (`callDBus`).
- Teclado: portal `org.freedesktop.portal.RemoteDesktop`. La primera vez KDE pregunta si
  se permite el control remoto del teclado; el permiso se recuerda (`restore_token`).
"""

from __future__ import annotations

import json
import logging
import secrets
import tempfile
import threading
import zlib
from pathlib import Path

from paste_photo.core.hotkey import parse_hotkey
from paste_photo.core.ports import WindowInfo
from paste_photo.paths import user_state_dir

log = logging.getLogger(__name__)

HELPER_NAME = "io.github.igarbayo.PastePhoto.KWinHelper"
HELPER_INTERFACE = "io.github.igarbayo.PastePhoto.KWin"

# Plasma 6 (windowList/activeWindow) y Plasma 5 (clientList/activeClient).
SCRIPT_HEADER = """
const wins = workspace.windowList ? workspace.windowList() : workspace.clientList();
const active = workspace.activeWindow !== undefined ? workspace.activeWindow
                                                    : workspace.activeClient;
"""
LIST_SCRIPT = SCRIPT_HEADER + """
const out = wins.filter(w => w.normalWindow).map(w => ({
  id: String(w.internalId), title: w.caption, pid: w.pid,
  app_id: String(w.resourceClass), active: w === active }));
callDBus("%(name)s", "/", "%(iface)s", "Report", JSON.stringify(out));
"""
ACTIVATE_SCRIPT = SCRIPT_HEADER + """
const w = wins.find(w => String(w.internalId) === "%(uuid)s");
if (w) { if (workspace.activeWindow !== undefined) workspace.activeWindow = w;
         else workspace.activeClient = w; }
callDBus("%(name)s", "/", "%(iface)s", "Report", w ? "ok" : "missing");
"""


def window_number(uuid: str) -> int:
    """KWin identifica ventanas por UUID; el puerto usa enteros."""
    return zlib.crc32(uuid.encode()) & 0x7FFFFFFF


def parse_report(payload: str) -> tuple[list[WindowInfo], dict[int, str], int | None]:
    windows, uuids, active = [], {}, None
    for w in json.loads(payload):
        number = window_number(w["id"])
        uuids[number] = w["id"]
        windows.append(WindowInfo(number, w.get("title") or "", int(w.get("pid") or 0),
                                  w.get("app_id") or ""))
        if w.get("active"):
            active = number
    return windows, uuids, active


class KWinWindowSystem:
    def __init__(self) -> None:
        self._uuids: dict[int, str] = {}
        self._lock = threading.Lock()

    def list_windows(self) -> list[WindowInfo]:
        windows, self._uuids, _active = parse_report(self._run_script(LIST_SCRIPT))
        return windows

    def active_window(self) -> int | None:
        _windows, self._uuids, active = parse_report(self._run_script(LIST_SCRIPT))
        return active

    def activate(self, window_id: int) -> None:
        uuid = self._uuids.get(window_id)
        if uuid is None:
            self.list_windows()
            uuid = self._uuids.get(window_id)
        if uuid is None or self._run_script(ACTIVATE_SCRIPT, uuid=uuid) != "ok":
            raise RuntimeError(f"KWin no encontró la ventana {window_id}")

    def _run_script(self, template: str, **values: str) -> str:
        from jeepney import DBusAddress, MatchRule, new_method_call, new_method_return
        from jeepney.bus_messages import message_bus
        from jeepney.io.blocking import open_dbus_connection

        source = template % {"name": HELPER_NAME, "iface": HELPER_INTERFACE, **values}
        plugin = f"paste-photo-{secrets.token_hex(4)}"
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
            fh.write(source)
            script_path = fh.name
        try:
            with self._lock, open_dbus_connection(bus="SESSION") as conn:
                conn.send_and_get_reply(message_bus.RequestName(HELPER_NAME))
                scripting = DBusAddress("/Scripting", bus_name="org.kde.KWin",
                                        interface="org.kde.kwin.Scripting")
                reply = conn.send_and_get_reply(
                    new_method_call(scripting, "loadScript", "ss", (script_path, plugin)))
                script_id = reply.body[0]
                # El filtro va ANTES de ejecutar: si no, el Report puede llegar mientras se
                # espera la respuesta de `run` y jeepney lo descartaría.
                report = MatchRule(type="method_call", interface=HELPER_INTERFACE,
                                   member="Report")
                try:
                    with conn.filter(report) as reports:
                        # Plasma 6: /Scripting/Script<N>; Plasma 5: /<N>.
                        for path in (f"/Scripting/Script{script_id}", f"/{script_id}"):
                            script = DBusAddress(path, bus_name="org.kde.KWin",
                                                 interface="org.kde.kwin.Script")
                            run = conn.send_and_get_reply(new_method_call(script, "run"))
                            if run.header.message_type.name != "error":
                                break
                        message = conn.recv_until_filtered(reports, timeout=3)
                        conn.send(new_method_return(message))
                        return message.body[0]
                finally:
                    conn.send_and_get_reply(
                        new_method_call(scripting, "unloadScript", "s", (plugin,)))
        finally:
            Path(script_path).unlink(missing_ok=True)


# --- Teclado: portal RemoteDesktop ---------------------------------------------------------

PORTAL = ("org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop")
KEYSYMS = {"ctrl": 0xFFE3, "alt": 0xFFE9, "shift": 0xFFE1, "win": 0xFFEB, "cmd": 0xFFEB}
DEVICE_KEYBOARD = 1
PERSIST_UNTIL_REVOKED = 2


def key_sequence(hotkey: str) -> list[tuple[int, int]]:
    """"ctrl+v" → [(keysym, 1=pulsar), ..., (keysym, 0=soltar)]. Puro: se prueba sin D-Bus."""
    parsed = parse_hotkey(hotkey)
    if len(parsed.key) != 1:
        raise ValueError(f"Solo teclas de un carácter: {hotkey}")
    syms = [KEYSYMS[m] for m in parsed.modifiers] + [ord(parsed.key)]
    return [(s, 1) for s in syms] + [(s, 0) for s in reversed(syms)]


class PortalKeyboard:
    """Sesión RemoteDesktop abierta una vez y reutilizada (el permiso se recuerda)."""

    def __init__(self, token_file: Path | None = None) -> None:
        self._token_file = token_file or user_state_dir() / "remote-desktop.token"
        self._conn = None
        self._session: str | None = None
        self._lock = threading.Lock()

    def send_hotkey(self, hotkey: str) -> None:
        from jeepney import DBusAddress, new_method_call

        with self._lock:
            if self._session is None:
                self._open()
            portal = DBusAddress(PORTAL[1], bus_name=PORTAL[0],
                                 interface="org.freedesktop.portal.RemoteDesktop")
            for keysym, state in key_sequence(hotkey):
                self._conn.send_and_get_reply(new_method_call(
                    portal, "NotifyKeyboardKeysym", "oa{sv}iu", (self._session, {}, keysym, state)))

    def _open(self) -> None:
        from jeepney.io.blocking import open_dbus_connection

        self._conn = open_dbus_connection(bus="SESSION")
        results = self._request("CreateSession", "a{sv}", lambda token: (
            {"handle_token": ("s", token), "session_handle_token": ("s", "pp" + token)},))
        self._session = results["session_handle"][1]
        options = {"types": ("u", DEVICE_KEYBOARD), "persist_mode": ("u", PERSIST_UNTIL_REVOKED)}
        if self._token_file.exists():
            options["restore_token"] = ("s", self._token_file.read_text().strip())
        self._request("SelectDevices", "oa{sv}", lambda token: (
            self._session, {**options, "handle_token": ("s", token)}))
        started = self._request("Start", "osa{sv}", lambda token: (
            self._session, "", {"handle_token": ("s", token)}), timeout=120)
        if "restore_token" in started:
            self._token_file.write_text(started["restore_token"][1])
            self._token_file.chmod(0o600)

    def _request(self, method: str, signature: str, make_args, timeout: float = 30) -> dict:
        """Llamada al portal con el patrón Request/Response (respuesta por señal)."""
        from jeepney import DBusAddress, MatchRule, new_method_call
        from jeepney.bus_messages import message_bus

        token = "pastephoto" + secrets.token_hex(4)
        sender = self._conn.unique_name.lstrip(":").replace(".", "_")
        path = f"/org/freedesktop/portal/desktop/request/{sender}/{token}"
        rule = MatchRule(type="signal", interface="org.freedesktop.portal.Request",
                         member="Response", path=path)
        self._conn.send_and_get_reply(message_bus.AddMatch(rule))
        portal = DBusAddress(PORTAL[1], bus_name=PORTAL[0],
                             interface="org.freedesktop.portal.RemoteDesktop")
        with self._conn.filter(rule) as queue:
            self._conn.send_and_get_reply(new_method_call(portal, method, signature,
                                                          make_args(token)))
            response = self._conn.recv_until_filtered(queue, timeout=timeout)
        code, results = response.body
        if code != 0:
            raise RuntimeError(f"El portal RemoteDesktop denegó {method} (código {code})")
        return results
