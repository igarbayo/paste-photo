# PyInstaller: dos ejecutables que comparten la misma carpeta (onedir) y dependencias.
#   paste-photo.exe      sin consola  -> icono en la bandeja (lo que abre el usuario)
#   paste-photo-cli.exe  con consola  -> `run`, `--probe`... desde una terminal
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

coll = COLLECT(gui, cli, a.binaries, a.datas, name="paste-photo", upx=False)
