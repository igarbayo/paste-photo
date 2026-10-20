# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Avisos de terceros para la distribución binaria (el instalador redistribuye dependencias).

    python packaging/third_party.py <carpeta de la app>    (lo llama build.py)

Escribe en la carpeta de la app:
    LICENSE                    licencia de PastePhoto (MIT)
    THIRD-PARTY-NOTICES.txt    resumen: componente, versión, licencia y dónde está su texto
    licenses/<componente>/...  textos completos copiados de cada paquete

Las dependencias se descubren solas (cierre de `Requires-Dist` de paste-photo para este SO),
así que una dependencia nueva no requiere tocar este archivo. Ver docs/COMPONENTS_LICENSE.md.
"""

from __future__ import annotations

import importlib.metadata as md
import re
import shutil
import sys
from pathlib import Path

from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parent.parent
LICENSE_FILE = re.compile(r"(LICEN[CS]E|COPYING|NOTICE)", re.I)

# Componentes que no son paquetes de Python pero viajan dentro del .exe.
EXTRA = [
    ("CPython runtime (python312.dll), with OpenSSL, libffi, bzip2, xz, expat and mpdecimal",
     None, "PSF-2.0 (the same file includes the licenses of its bundled libraries)", "python"),
    ("PyInstaller bootloader", None,
     "GPL-2.0-or-later WITH Bootloader-exception (allows any license for the bundled app)",
     "pyinstaller"),
    ("Microsoft Visual C++ Runtime and Universal CRT (vcruntime140*.dll, ucrtbase.dll, api-ms-*)",
     None, "Microsoft redistributable code (Visual Studio / Windows SDK)", None),
]

LGPL_NOTE = """\
pystray (LGPL-3.0-or-later)
---------------------------
PastePhoto uses the pystray library, licensed under the GNU Lesser General Public License
v3 or later. The full LGPL and GPL texts are in licenses/pystray/ (COPYING.LGPL, COPYING).
pystray is shipped as plain, unmodified Python source files in _internal/pystray/, so you can
replace it with a modified or newer version: PastePhoto loads it from there at runtime.
Source code: https://github.com/moses-palmer/pystray
"""


def runtime_distributions(root: str = "paste-photo") -> list[md.Distribution]:
    """Dependencias de ejecución (transitivas) de paste-photo en este SO, sin extras."""
    seen: dict[str, md.Distribution] = {}

    def walk(name: str) -> None:
        dist = md.distribution(name)
        key = dist.metadata["Name"].lower().replace("_", "-")
        if key in seen:
            return
        seen[key] = dist
        for raw in dist.requires or []:
            req = Requirement(raw)
            if req.marker and not req.marker.evaluate({"extra": ""}):
                continue
            walk(req.name)

    walk(root)
    seen.pop(root, None)
    return sorted(seen.values(), key=lambda d: d.metadata["Name"].lower())


def license_of(dist: md.Distribution) -> str:
    meta = dist.metadata
    expression = meta.get("License-Expression")
    if expression:
        return expression
    text = (meta.get("License") or "").strip()
    if text and len(text) < 80 and "\n" not in text:
        return text
    classifiers = [c.split("::")[-1].strip() for c in meta.get_all("Classifier") or []
                   if c.startswith("License ::")]
    return ", ".join(classifiers) or "see its license files"


def license_files(dist: md.Distribution) -> list[tuple[Path, str]]:
    """(archivo, nombre de destino). El nombre conserva la subruta dentro de .dist-info para
    que no se pisen (pywin32 trae varias `License.txt` en subcarpetas)."""
    found = []
    for f in dist.files or []:
        parts = f.parts
        if parts and parts[0].endswith(".dist-info") and LICENSE_FILE.search(f.name):
            inner = [p for p in parts[1:] if p != "licenses"]
            found.append((Path(dist.locate_file(f)), "__".join(inner)))
    return found


def write_notices(app_dir: Path) -> Path:
    out = app_dir / "licenses"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    shutil.copy2(ROOT / "LICENSE", app_dir / "LICENSE")

    rows: list[tuple[str, str, str, str]] = []
    for dist in runtime_distributions():
        name = dist.metadata["Name"]
        folder = out / name.lower()
        for src, target in license_files(dist):
            folder.mkdir(exist_ok=True)
            shutil.copy2(src, folder / target)
        rows.append((name, dist.version, license_of(dist), f"licenses/{name.lower()}/"))

    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if python_license.exists():
        (out / "python").mkdir()
        shutil.copy2(python_license, out / "python" / "LICENSE.txt")
    try:
        pyinstaller = md.distribution("pyinstaller")
        (out / "pyinstaller").mkdir()
        for src, target in license_files(pyinstaller):
            shutil.copy2(src, out / "pyinstaller" / target)
        pyinstaller_version = pyinstaller.version
    except md.PackageNotFoundError:
        pyinstaller_version = ""
    for title, _version, lic, folder in EXTRA:
        version = {"python": sys.version.split()[0], "pyinstaller": pyinstaller_version}.get(
            folder or "", "")
        rows.append((title, version, lic, f"licenses/{folder}/" if folder else "-"))

    notices = app_dir / "THIRD-PARTY-NOTICES.txt"
    notices.write_text(render(rows), encoding="utf-8")
    return notices


def render(rows: list[tuple[str, str, str, str]]) -> str:
    lines = [
        "PastePhoto - third-party notices",
        "==================================",
        "",
        "PastePhoto itself is licensed under the MIT License (see LICENSE).",
        "This distribution also includes the following third-party components, each under its",
        "own license. Full texts are in the licenses/ folder next to this file.",
        "",
    ]
    for name, version, lic, where in rows:
        lines.append(f"- {name}" + (f" {version}" if version else ""))
        lines.append(f"  License: {lic}")
        if where != "-":
            lines.append(f"  Text:    {where}")
        lines.append("")
    lines += [LGPL_NOTE, "All components are provided WITHOUT ANY WARRANTY; see their licenses.",
              ""]
    return "\n".join(lines)


if __name__ == "__main__":
    print(write_notices(Path(sys.argv[1])))
