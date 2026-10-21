# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT
# PyInstaller: PastePhoto.app (sin firmar; PyInstaller le pone una firma ad hoc).
#   Contents/MacOS/paste-photo              la app (barra de menús; `doctor`, `run`... en terminal)
#   Contents/MacOS/paste-photo-native-host  lo lanza el navegador (extensión de PastePhoto)
# Uso: python packaging/build.py  (en macOS; necesita la versión en PASTE_PHOTO_VERSION)
# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH).resolve().parent.parent  # noqa: F821 - SPECPATH lo define PyInstaller
HERE = ROOT / "packaging" / "macos"
VERSION = os.environ["PASTE_PHOTO_VERSION"]

# Los destinos y plataformas se importan por nombre (registro de plugins): hay que declararlos.
hiddenimports = collect_submodules("paste_photo") + collect_submodules("pystray")

a = Analysis(
    [str(ROOT / "packaging" / "windows" / "entry.py")],  # el nombre del ejecutable decide el papel
    pathex=[str(ROOT)],
    datas=collect_data_files("paste_photo"),
    hiddenimports=hiddenimports,
    runtime_hooks=[str(HERE / "rthook_env.py")],
    excludes=["tkinter", "pytest", "ruff"],
    noarchive=False,
    # LGPL-3.0: pystray como archivos .py sueltos, sustituibles. Ver docs/COMPONENTS_LICENSE.md.
    module_collection_mode={"pystray": "py"},
)
pyz = PYZ(a.pure)


def exe(name):
    return EXE(pyz, a.scripts, [], exclude_binaries=True, name=name, console=False,
               argv_emulation=False, upx=False)


app = exe("paste-photo")  # el primero es el ejecutable principal del .app
host = exe("paste-photo-native-host")
coll = COLLECT(app, host, a.binaries, a.datas, name="paste-photo", upx=False)

BUNDLE(
    coll,
    name="PastePhoto.app",
    icon=str(HERE / "icon.icns"),
    bundle_identifier="io.github.igarbayo.paste-photo",
    version=VERSION,
    info_plist={
        "CFBundleName": "PastePhoto",
        "CFBundleDisplayName": "PastePhoto",
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": VERSION,
        "LSUIElement": True,  # solo en la barra de menús, no en el Dock
        "LSMinimumSystemVersion": "12.0",
        "NSHighResolutionCapable": True,
        "NSHumanReadableCopyright": "© 2026 igarbayo. MIT License.",
        "NSAppleEventsUsageDescription": (
            "PastePhoto controls Terminal, iTerm2, Safari and Chrome to paste your "
            "screenshots into Claude."
        ),
    },
)
