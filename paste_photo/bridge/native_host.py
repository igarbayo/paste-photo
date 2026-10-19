# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""`paste-photo-native-host`: lo lanza el navegador (native messaging), no el usuario.

Reenvía mensajes entre la extensión (stdin/stdout del host) y el servicio de paste-photo
(canal local). Si el servicio no está abierto, espera y reintenta: la extensión sigue
conectada y estará lista en cuanto se abra paste-photo.
"""

from __future__ import annotations

import sys
import threading
import time
from multiprocessing.connection import Client, Connection

from paste_photo.bridge import protocol

RETRY_S = 2.0


def main() -> int:
    stdin, stdout = sys.stdin.buffer, sys.stdout.buffer
    out_lock = threading.Lock()
    state: dict[str, Connection | dict | None] = {"conn": None, "hello": None}
    closed = threading.Event()

    def to_browser(message: dict) -> None:
        with out_lock:
            protocol.write_native(stdout, message)

    def service_loop() -> None:
        while not closed.is_set():
            try:
                conn = Client(protocol.address(), family=protocol.family(),
                              authkey=protocol.authkey())
            except (OSError, EOFError):
                time.sleep(RETRY_S)  # paste-photo no está abierto todavía
                continue
            state["conn"] = conn
            if state["hello"] is not None:  # presentarse de nuevo tras reconectar
                conn.send_bytes(protocol.encode(state["hello"]))
            try:
                while True:
                    to_browser(protocol.decode(conn.recv_bytes()))
            except (OSError, EOFError):
                state["conn"] = None  # el servicio se cerró: volver a esperar

    threading.Thread(target=service_loop, name="service", daemon=True).start()
    while True:
        message = protocol.read_native(stdin)
        if message is None:  # el navegador cerró la extensión o se cerró él mismo
            closed.set()
            return 0
        if message.get("event") == "hello":
            state["hello"] = message
        conn = state["conn"]
        if conn is not None:
            try:
                conn.send_bytes(protocol.encode(message))
            except (OSError, EOFError):
                state["conn"] = None


if __name__ == "__main__":
    sys.exit(main())
