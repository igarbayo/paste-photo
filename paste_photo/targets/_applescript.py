# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""AppleScript desde Python (`osascript`), para los destinos de macOS.

Los datos variables se pasan como argumentos (`on run argv`), nunca dentro del texto del
script. La primera vez que se controla cada app, macOS pide el permiso de Automatización.
"""

from __future__ import annotations

import subprocess

TIMEOUT_S = 5
FIELD_SEP = "\t"


def osascript(script: str, *args: str, timeout: float = TIMEOUT_S) -> str:
    result = subprocess.run(["osascript", "-", *args], input=script, capture_output=True,
                            text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"osascript: {result.stderr.strip() or result.returncode}")
    return result.stdout.rstrip("\n")


def parse_rows(output: str, fields: int) -> list[list[str]]:
    """Filas separadas por saltos de línea y campos por tabuladores (el último campo puede
    contener tabuladores: se queda con el resto de la línea)."""
    rows = []
    for line in output.splitlines():
        parts = line.split(FIELD_SEP, fields - 1)
        if len(parts) == fields:
            rows.append(parts)
    return rows
