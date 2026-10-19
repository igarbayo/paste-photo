# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Lado del servicio: acepta conexiones de los hosts nativos (uno por navegador abierto)."""

from __future__ import annotations

import itertools
import logging
import sys
import threading
from concurrent.futures import Future
from concurrent.futures import TimeoutError as FutureTimeout
from multiprocessing.connection import Connection, Listener
from pathlib import Path
from typing import Any

from paste_photo.bridge import protocol

log = logging.getLogger(__name__)


class BridgeError(RuntimeError):
    pass


class BrowserClient:
    """Una extensión conectada (a través de su host nativo)."""

    def __init__(self, conn: Connection, server: BridgeServer) -> None:
        self._conn = conn
        self._server = server
        self._send_lock = threading.Lock()
        self._pending: dict[int, Future[dict[str, Any]]] = {}
        self._ids = itertools.count(1)
        self.info: dict[str, Any] = {}
        self.alive = True
        threading.Thread(target=self._read, name="bridge-client", daemon=True).start()

    def request(self, message: dict[str, Any], timeout: float) -> dict[str, Any]:
        request_id = next(self._ids)
        future: Future[dict[str, Any]] = Future()
        self._pending[request_id] = future
        try:
            with self._send_lock:
                self._conn.send_bytes(protocol.encode({"id": request_id, **message}))
            return future.result(timeout=timeout)
        except FutureTimeout:
            raise BridgeError(f"la extensión no respondió a {message.get('cmd')}") from None
        except (OSError, EOFError) as error:
            self._close()
            raise BridgeError(f"conexión con la extensión perdida: {error}") from None
        finally:
            self._pending.pop(request_id, None)

    def _read(self) -> None:
        try:
            while True:
                message = protocol.decode(self._conn.recv_bytes())
                if message.get("event") == "hello":
                    self.info = message
                    log.info("Extensión del navegador conectada (v%s)", message.get("version"))
                elif message.get("cmd") == "status":  # `paste-photo doctor`
                    browsers = [c.info for c in self._server.clients() if c.info]
                    with self._send_lock:
                        self._conn.send_bytes(protocol.encode({"browsers": browsers}))
                elif "id" in message and (future := self._pending.get(message["id"])):
                    future.set_result(message)
        except (OSError, EOFError, ValueError):
            pass
        finally:
            self._close()

    def _close(self) -> None:
        if self.alive:
            self.alive = False
            self._server._forget(self)
            for future in self._pending.values():
                if not future.done():
                    future.set_exception(EOFError("desconectado"))
            try:
                self._conn.close()
            except OSError:
                pass


class BridgeServer:
    """Escucha en el canal local. Una sola instancia por proceso (`instance()`)."""

    _instance: BridgeServer | None = None
    _instance_lock = threading.Lock()

    def __init__(self, address: str | None = None, authkey: bytes | None = None) -> None:
        self.address = address or protocol.address()
        self._authkey = authkey if authkey is not None else protocol.authkey()
        self._clients: list[BrowserClient] = []
        self._lock = threading.Lock()
        self._listener: Listener | None = None

    @classmethod
    def instance(cls) -> BridgeServer:
        with cls._instance_lock:
            if cls._instance is None:
                server = cls()
                server.start()
                cls._instance = server
            return cls._instance

    def start(self) -> None:
        if protocol.family() == "AF_UNIX":
            # Restos de una ejecución anterior que terminó mal (solo hay una instancia).
            Path(self.address).unlink(missing_ok=True)
        self._listener = Listener(self.address, family=protocol.family(), authkey=self._authkey)
        if sys.platform != "win32":
            Path(self.address).chmod(0o600)
        threading.Thread(target=self._accept, name="bridge-accept", daemon=True).start()
        log.debug("Puente del navegador escuchando en %s", self.address)

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.close()
            self._listener = None
        for client in self.clients():
            client._close()

    def clients(self) -> list[BrowserClient]:
        with self._lock:
            return [c for c in self._clients if c.alive]

    def _accept(self) -> None:
        while self._listener is not None:
            try:
                conn = self._listener.accept()
            except (OSError, EOFError) as error:
                if self._listener is None:
                    return
                log.debug("Conexión rechazada en el puente: %s", error)  # p. ej. authkey mala
                continue
            with self._lock:
                self._clients.append(BrowserClient(conn, self))

    def _forget(self, client: BrowserClient) -> None:
        with self._lock:
            if client in self._clients:
                self._clients.remove(client)
