# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Puente con la extensión: formato native messaging, troceo y relevo real con el host."""

import io
import json
import os
import secrets
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import pytest

from paste_photo.bridge import protocol
from paste_photo.core.events import ScreenshotCaptured
from paste_photo.targets.browser_extension import BrowserExtensionTarget


def reassemble(stream: io.BytesIO) -> list[dict]:
    """Lo mismo que hace background.js con los trozos."""
    messages, parts = [], {}
    while (msg := protocol.read_native(stream)) is not None:
        if "chunk" in msg:
            parts.setdefault(msg["chunk"], [None] * msg["total"])[msg["seq"]] = msg["data"]
            if None not in parts[msg["chunk"]]:
                messages.append(json.loads("".join(parts.pop(msg["chunk"]))))
        else:
            messages.append(msg)
    return messages


def test_native_framing_roundtrip():
    stream = io.BytesIO()
    protocol.write_native(stream, {"id": 1, "cmd": "list"})
    stream.seek(0)
    assert protocol.read_native(stream) == {"id": 1, "cmd": "list"}
    assert protocol.read_native(stream) is None


def test_big_messages_are_chunked_under_browser_limit():
    big = {"id": 7, "cmd": "paste", "png": "A" * (3 * 1024 * 1024)}  # 3 MB
    stream = io.BytesIO()
    protocol.write_native(stream, big)
    raw = stream.getvalue()
    # Ningún mensaje individual supera 1 MB (límite de Chrome para el host).
    offset, sizes = 0, []
    while offset < len(raw):
        size = int.from_bytes(raw[offset:offset + 4], sys.byteorder)
        sizes.append(size)
        offset += 4 + size
    assert len(sizes) > 1 and max(sizes) < protocol.MAX_HOST_MESSAGE
    assert reassemble(io.BytesIO(raw)) == [big]


@pytest.fixture
def isolated_bridge(tmp_path, monkeypatch):
    if sys.platform == "win32":
        address = rf"\\.\pipe\paste-photo-test-{secrets.token_hex(4)}"
    else:  # rutas de socket cortas (límite de 108 caracteres)
        address = os.path.join(tempfile.gettempdir(), f"pp-{secrets.token_hex(4)}.sock")
    monkeypatch.setenv("PASTE_PHOTO_BRIDGE_ADDRESS", address)
    monkeypatch.setenv("PASTE_PHOTO_STATE_DIR", str(tmp_path / "state"))
    from paste_photo.bridge.server import BridgeServer

    server = BridgeServer()
    server.start()
    yield server
    server.stop()


def test_relay_between_service_host_and_browser(isolated_bridge):
    root = Path(__file__).resolve().parent.parent
    host = subprocess.Popen([sys.executable, "-m", "paste_photo.bridge.native_host"],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, cwd=root,
                            env=dict(os.environ))
    try:
        protocol.write_native(host.stdin, {"event": "hello", "version": "test"})
        deadline = time.time() + 10
        while not isolated_bridge.clients() and time.time() < deadline:
            time.sleep(0.05)
        (client,) = isolated_bridge.clients()

        # "Navegador" simulado: lee lo que el host le manda y responde.
        def browser() -> None:
            received = []
            while len(received) < 2:
                msg = protocol.read_native(host.stdout)
                if "chunk" in msg:
                    received.append(msg)
                    buf = [msg]
                    while len(buf) < msg["total"]:
                        buf.append(protocol.read_native(host.stdout))
                    ordered = sorted(buf, key=lambda p: p["seq"])
                    full = json.loads("".join(p["data"] for p in ordered))
                    protocol.write_native(host.stdin, {"id": full["id"], "ok": True,
                                                       "size": len(full["png"])})
                else:
                    received.append(msg)
                    protocol.write_native(host.stdin, {"id": msg["id"], "ok": True,
                                                       "tabs": [{"tabId": 5}]})

        threading.Thread(target=browser, daemon=True).start()
        assert client.request({"cmd": "list"}, timeout=10)["tabs"] == [{"tabId": 5}]
        reply = client.request({"cmd": "paste", "png": "B" * 2_000_000}, timeout=20)
        assert reply == {"id": reply["id"], "ok": True, "size": 2_000_000}
        assert client.info["version"] == "test"
    finally:
        host.stdin.close()
        host.wait(timeout=10)


# --- destino browser_extension con clientes falsos ---------------------------------------


class FakeClient:
    def __init__(self, tabs, accept=()):
        self.tabs, self.accept, self.pasted = tabs, set(accept), []

    def request(self, message, timeout):
        if message["cmd"] == "list":
            return {"ok": True, "tabs": self.tabs}
        self.pasted.append(message["tabId"])
        ok = message["tabId"] in self.accept
        return {"ok": ok, "error": None if ok else "no-editor"}


class FakeServer:
    def __init__(self, clients):
        self._clients = clients

    def clients(self):
        return self._clients


def shot() -> ScreenshotCaptured:
    return ScreenshotCaptured("abc123", 0.0, load_png=lambda: b"\x89PNG fake")


def test_extension_target_prefers_most_recent_tab_and_skips_unready():
    old = {"tabId": 1, "url": "https://claude.ai/chat/1", "title": "Viejo - Claude",
           "lastUsed": 1_000_000, "active": False}
    new = {"tabId": 2, "url": "https://claude.ai/new", "title": "Nuevo chat - Claude",
           "lastUsed": 2_000_000, "active": True}
    # La usada más recientemente es un artifact (tiene editor, pero no es un chat): fuera.
    doc = {"tabId": 3, "url": "https://claude.ai/artifact/abc", "title": "Doc - Claude",
           "lastUsed": 3_000_000, "active": True}
    client = FakeClient([old, new, doc], accept={1, 3})
    target = BrowserExtensionTarget(server=FakeServer([client]))
    handle = target.locate()
    assert handle.label == "Nuevo chat - Claude" and handle.extra["last_used"] == 2000.0
    target.paste(handle, shot())
    assert client.pasted == [2, 1]  # la 2 no tenía editor: se prueba la siguiente


def test_extension_target_ignores_non_chat_tabs():
    tabs = [{"tabId": 1, "url": "https://claude.ai/code/artifact/x", "title": "Doc"},
            {"tabId": 2, "url": "https://claude.ai/recents", "title": "Claude"}]
    assert BrowserExtensionTarget(server=FakeServer([FakeClient(tabs)])).locate() is None


def test_extension_target_without_browsers():
    assert BrowserExtensionTarget(server=FakeServer([])).locate() is None
