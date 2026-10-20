# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Genera la extensión de Firefox (.xpi) a partir de la de Chromium.

    python packaging/firefox_xpi.py dist/paste-photo-firefox-X.Y.Z.xpi

La firma (obligatoria para instalarla en Firefox normal) la hace la release con `web-ext sign`
si hay credenciales de addons.mozilla.org; ver `.github/workflows/release.yml`.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from paste_photo.bridge.install import build_firefox_extension  # noqa: E402


def main() -> int:
    target = Path(sys.argv[1]).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        xpi = build_firefox_extension(Path(tmp) / "extension-firefox")
        shutil.copy(xpi, target)
        # La carpeta descomprimida, para `web-ext sign --source-dir`.
        source = target.with_suffix("")
        shutil.rmtree(source, ignore_errors=True)
        shutil.copytree(Path(tmp) / "extension-firefox", source)
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
