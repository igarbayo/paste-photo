"""Punto de entrada de los .exe (PyInstaller necesita un script, no un módulo)."""

import sys

from paste_photo.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
