# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT
# PyInstaller: dos ejecutables que comparten la misma carpeta (onedir) y dependencias.
#   paste-photo.exe      sin consola  -> icono en la bandeja (lo que abre el usuario)
#   paste-photo-cli.exe  con consola  -> `run`, `--probe`... desde una terminal
#   paste-photo-native-host.exe       -> lo lanza el navegador (extensión de PastePhoto)
# Uso: pyinstaller packaging/windows/paste-photo.spec  (o python packaging/build.py)
# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

ROOT = Path(SPECPATH).resolve().parent.parent  # noqa: F821 - SPECPATH lo define PyInstaller
ICON = str(ROOT / "paste_photo" / "resources" / "icon.ico")

# Los destinos y plataformas se importan por nombre (registro de plugins): hay que declararlos.
hiddenimports = (
    collect_submodules("paste_photo")
    + collect_submodules("pystray")
    + ["win32timezone"]
)

a = Analysis(
    [str(ROOT / "packaging" / "windows" / "entry.py")],
    pathex=[str(ROOT)],
    binaries=collect_dynamic_libs("uiautomation"),
    datas=collect_data_files("paste_photo") + collect_data_files("uiautomation"),
    hiddenimports=hiddenimports,
    excludes=["tkinter", "pytest", "ruff"],
    noarchive=False,
    # LGPL-3.0: pystray va como archivos .py sueltos en _internal/pystray (no dentro del
    # archivo comprimido) para que el usuario pueda sustituirlo. Ver docs/COMPONENTS_LICENSE.md.
    module_collection_mode={"pystray": "py"},
)
pyz = PYZ(a.pure)


def exe(name, console):
    return EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name=name,
        console=console,
        icon=ICON,
        version=str(ROOT / "build" / "version_info.txt"),
        upx=False,
    )


gui = exe("paste-photo", console=False)
cli = exe("paste-photo-cli", console=True)
# Native messaging: el navegador lo lanza con stdin/stdout (consola, pero sin ventana).
host = exe("paste-photo-native-host", console=True)

coll = COLLECT(gui, cli, host, a.binaries, a.datas, name="paste-photo", upx=False)
