# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Hook de PyInstaller del .app: se ejecuta antes que PastePhoto.

Abierto desde Finder, el .app hereda de launchd un PATH mínimo (`/usr/bin:/bin:...`) y ningún
LANG: sin esto no se encontrarían `tmux`, `kitty` ni `wezterm` de Homebrew.
"""

import os

_EXTRA = ("/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin", "/usr/sbin", "/sbin")
_parts = [p for p in os.environ.get("PATH", "").split(os.pathsep) if p]
os.environ["PATH"] = os.pathsep.join(dict.fromkeys(_parts + list(_EXTRA)))
os.environ.setdefault("LANG", "en_US.UTF-8")
