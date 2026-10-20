# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Construye el paquete .deb (arquitectura `all`: solo Python).

    python3 packaging/linux/build_deb.py        # → dist/paste-photo_X.Y.Z_all.deb

Usa las dependencias de Python que ya empaquetan Debian/Ubuntu (Pillow, psutil, python-xlib,
jeepney, tomlkit) y solo incluye pystray (+ six no hace falta: Debian lo trae) como código
fuente en /usr/lib/paste-photo/vendor, porque no está en los repositorios. Requiere
`dpkg-deb` (paquete dpkg) y pystray instalado en el Python que ejecuta el script.
"""

from __future__ import annotations

import gzip
import importlib.util
import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "dist"
STAGE_ROOT = ROOT / "build" / "deb"
LIB = Path("usr/lib/paste-photo")

DEPENDS = [
    "python3 (>= 3.11)", "python3-pil", "python3-psutil", "python3-xlib", "python3-jeepney",
    "python3-tomlkit", "python3-six",
]
RECOMMENDS = ["xclip | wl-clipboard", "python3-gi", "gir1.2-ayatanaappindicator3-0.1"]
SUGGESTS = ["tmux", "xdotool"]

LAUNCHER = """#!/bin/sh
# paste-photo (.deb): el paquete vive en /usr/lib/paste-photo.
export PYTHONPATH="/usr/lib/paste-photo:/usr/lib/paste-photo/vendor${PYTHONPATH:+:$PYTHONPATH}"
export PASTE_PHOTO_LAUNCH=/usr/bin/paste-photo
exec /usr/bin/python3 -m %(module)s "$@"
"""

DESKTOP = """[Desktop Entry]
Type=Application
Name=paste-photo
Comment=Paste your screenshots into Claude
Exec=paste-photo
Icon=paste-photo
Terminal=false
Categories=Utility;
StartupNotify=false
"""

COPYRIGHT = """Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: paste-photo
Upstream-Contact: https://github.com/igarbayo/paste-photo/issues
Source: https://github.com/igarbayo/paste-photo

Files: *
Copyright: 2026 igarbayo
License: MIT

Files: usr/lib/paste-photo/vendor/pystray/*
Copyright: Moses Palmér
License: LGPL-3+
 pystray is shipped as unmodified Python source so it can be replaced.
 On Debian systems, the full text of the GNU Lesser General Public License
 version 3 can be found in `/usr/share/common-licenses/LGPL-3'.

License: MIT
"""


def version() -> str:
    text = (ROOT / "paste_photo" / "__init__.py").read_text(encoding="utf-8")
    return re.search(r'__version__\s*=\s*"([^"]+)"', text).group(1)


def control(ver: str, installed_kb: int) -> str:
    return (
        "Package: paste-photo\n"
        f"Version: {ver}\n"
        "Architecture: all\n"
        "Maintainer: igarbayo <igarbayo@users.noreply.github.com>\n"
        f"Installed-Size: {installed_kb}\n"
        f"Depends: {', '.join(DEPENDS)}\n"
        f"Recommends: {', '.join(RECOMMENDS)}\n"
        f"Suggests: {', '.join(SUGGESTS)}\n"
        "Section: utils\n"
        "Priority: optional\n"
        "Homepage: https://github.com/igarbayo/paste-photo\n"
        "Description: Automatically paste your screenshots into Claude\n"
        " paste-photo lives in the system tray and pastes every new screenshot into\n"
        " the Claude you used last: Claude Code in any terminal (tmux, kitty, WezTerm,\n"
        " Konsole, Orca, GNOME Terminal, xterm...) or claude.ai in Chromium-based\n"
        " browsers, Firefox and other browsers such as GNOME Web.\n"
    )


def build() -> Path:
    ver = version()
    stage = STAGE_ROOT / f"paste-photo_{ver}_all"
    shutil.rmtree(stage, ignore_errors=True)
    lib = stage / LIB

    shutil.copytree(ROOT / "paste_photo", lib / "paste_photo",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "CLAUDE.md"))
    pystray = importlib.util.find_spec("pystray")
    if pystray is None or pystray.origin is None:
        raise SystemExit("pystray no está instalado en este Python: pip install pystray")
    shutil.copytree(Path(pystray.origin).parent, lib / "vendor" / "pystray",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    bin_dir = stage / "usr" / "bin"
    bin_dir.mkdir(parents=True)
    for name, module in (("paste-photo", "paste_photo"),
                         ("paste-photo-native-host", "paste_photo.bridge.native_host")):
        launcher = bin_dir / name
        launcher.write_text(LAUNCHER % {"module": module}, encoding="utf-8")
        launcher.chmod(0o755)

    share = stage / "usr" / "share"
    (share / "applications").mkdir(parents=True)
    (share / "applications" / "paste-photo.desktop").write_text(DESKTOP, encoding="utf-8")
    icon_dir = share / "icons" / "hicolor" / "256x256" / "apps"
    icon_dir.mkdir(parents=True)
    shutil.copy2(ROOT / "paste_photo" / "resources" / "icon.png", icon_dir / "paste-photo.png")
    doc = share / "doc" / "paste-photo"
    doc.mkdir(parents=True)
    mit = (ROOT / "LICENSE").read_text(encoding="utf-8")
    (doc / "copyright").write_text(COPYRIGHT + "".join(f" {line}\n" if line else " .\n"
                                                      for line in mit.splitlines()),
                                   encoding="utf-8")
    with gzip.open(doc / "changelog.gz", "wb", compresslevel=9) as fh:
        fh.write((ROOT / "CHANGELOG.md").read_bytes())

    size_kb = sum(f.stat().st_size for f in stage.rglob("*") if f.is_file()) // 1024 + 1
    (stage / "DEBIAN").mkdir()
    (stage / "DEBIAN" / "control").write_text(control(ver, size_kb), encoding="utf-8")
    for path in stage.rglob("*"):  # permisos estándar de Debian
        if path.is_dir():
            path.chmod(0o755)
        elif path.parent != bin_dir:
            path.chmod(0o644)

    DIST.mkdir(exist_ok=True)
    out = DIST / f"paste-photo_{ver}_all.deb"
    subprocess.run(["dpkg-deb", "--build", "--root-owner-group", str(stage), str(out)],
                   check=True, env={**os.environ, "SOURCE_DATE_EPOCH": "0"})
    print(f"OK: {out}")
    return out


if __name__ == "__main__":
    build()
