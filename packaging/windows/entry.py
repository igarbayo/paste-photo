# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Punto de entrada de los .exe (PyInstaller necesita un script, no un módulo).

Los tres ejecutables comparten este script; el nombre decide el papel:
    paste-photo.exe / paste-photo-cli.exe   la app (bandeja o consola)
    paste-photo-native-host.exe             host de native messaging (lo lanza el navegador)
"""

import sys
from pathlib import Path

if __name__ == "__main__":
    if Path(sys.executable).stem == "paste-photo-native-host":
        from paste_photo.bridge.native_host import main
    else:
        from paste_photo.__main__ import main
    sys.exit(main())
