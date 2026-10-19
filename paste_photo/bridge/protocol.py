# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Constantes y formato de los mensajes del puente (compartidos por servicio y host)."""

from __future__ import annotations

import getpass
import json
import os
import secrets
import struct
import sys
from pathlib import Path
from typing import Any, BinaryIO

from paste_photo.paths import user_state_dir

HOST_NAME = "io.github.igarbayo.paste_photo"
# ID fijo de la extensión: deriva de la clave pública ("key") de su manifest.json.
EXTENSION_ID = "dhoiaidcfkhhohlacfpjealcoigcncac"
EXTENSION_ORIGIN = f"chrome-extension://{EXTENSION_ID}/"

# El navegador no acepta mensajes del host de más de 1 MB: se trocean.
MAX_HOST_MESSAGE = 1024 * 1024
CHUNK_SIZE = 768 * 1024


def address() -> str:
    """Dirección del canal local entre el servicio y el host."""
    if override := os.environ.get("PASTE_PHOTO_BRIDGE_ADDRESS"):  # pruebas aisladas
        return override
    if sys.platform == "win32":
        return rf"\\.\pipe\paste-photo-{getpass.getuser()}"
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if runtime and Path(runtime).is_dir():
        return str(Path(runtime) / "paste-photo.sock")
    return f"/tmp/paste-photo-{os.getuid()}.sock"


def family() -> str:
    return "AF_PIPE" if sys.platform == "win32" else "AF_UNIX"


def authkey() -> bytes:
    """Secreto compartido (archivo privado del usuario): solo sus procesos pueden conectarse."""
    path = user_state_dir() / "bridge.key"
    if not path.exists():
        path.write_bytes(secrets.token_bytes(32))
        if sys.platform != "win32":
            path.chmod(0o600)
    return path.read_bytes()


# --- native messaging: 4 bytes de longitud (orden nativo) + JSON UTF-8 ---------------


def read_native(stream: BinaryIO) -> dict[str, Any] | None:
    header = stream.read(4)
    if len(header) < 4:
        return None  # el navegador cerró la conexión
    (length,) = struct.unpack("=I", header)
    return json.loads(stream.read(length).decode("utf-8"))


def write_native(stream: BinaryIO, message: dict[str, Any]) -> None:
    """Escribe un mensaje hacia el navegador, troceándolo si supera 1 MB."""
    data = json.dumps(message, separators=(",", ":"))
    if len(data.encode("utf-8")) < MAX_HOST_MESSAGE - 1024:
        _write_raw(stream, data.encode("utf-8"))
        return
    parts = [data[i : i + CHUNK_SIZE] for i in range(0, len(data), CHUNK_SIZE)]
    chunk_id = secrets.token_hex(4)
    for seq, part in enumerate(parts):
        piece = {"chunk": chunk_id, "seq": seq, "total": len(parts), "data": part}
        _write_raw(stream, json.dumps(piece, separators=(",", ":")).encode("utf-8"))


def _write_raw(stream: BinaryIO, payload: bytes) -> None:
    stream.write(struct.pack("=I", len(payload)) + payload)
    stream.flush()


def encode(message: dict[str, Any]) -> bytes:
    return json.dumps(message, separators=(",", ":")).encode("utf-8")


def decode(payload: bytes) -> dict[str, Any]:
    return json.loads(payload.decode("utf-8"))
