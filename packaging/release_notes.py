"""Imprime la sección de una versión del CHANGELOG (notas de la release de GitHub).

    python packaging/release_notes.py 0.2.0
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

CHANGELOG = Path(__file__).resolve().parent.parent / "CHANGELOG.md"


def notes(version: str, text: str) -> str:
    match = re.search(rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|^\[[^\]]+\]: |\Z)",
                      text, flags=re.S | re.M)
    if not match:
        raise SystemExit(f"No hay sección [{version}] en el CHANGELOG")
    return match.group(1).strip() + "\n"


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(notes(sys.argv[1], CHANGELOG.read_text(encoding="utf-8")), end="")
