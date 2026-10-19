# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""`paste-photo setup browser`: registra el host nativo en los navegadores Chromium y deja
la extensión en una carpeta estable para cargarla como "descomprimida"."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from paste_photo import resources
from paste_photo.bridge import protocol
from paste_photo.paths import user_data_dir

# Linux: carpetas de configuración de cada navegador (por usuario).
LINUX_BROWSER_DIRS = {
    "Google Chrome": "google-chrome",
    "Google Chrome Beta": "google-chrome-beta",
    "Google Chrome Dev": "google-chrome-unstable",
    "Chromium": "chromium",
    "Microsoft Edge": "microsoft-edge",
    "Brave": "BraveSoftware/Brave-Browser",
    "Vivaldi": "vivaldi",
    "Opera": "opera",
}
# Windows: claves de registro (HKCU) donde cada navegador busca hosts nativos.
WINDOWS_REGISTRY_KEYS = {
    "Google Chrome": r"Software\Google\Chrome\NativeMessagingHosts",
    "Chromium": r"Software\Chromium\NativeMessagingHosts",
    "Microsoft Edge": r"Software\Microsoft\Edge\NativeMessagingHosts",
    "Brave": r"Software\BraveSoftware\Brave-Browser\NativeMessagingHosts",
    "Vivaldi": r"Software\Vivaldi\NativeMessagingHosts",
}


def host_executable() -> Path:
    """Ruta absoluta de `paste-photo-native-host` (el navegador no admite argumentos)."""
    if getattr(sys, "frozen", False):  # .exe de PyInstaller: va junto a los demás
        return Path(sys.executable).with_name("paste-photo-native-host.exe")
    name = "paste-photo-native-host" + (".exe" if sys.platform == "win32" else "")
    beside = Path(sys.executable).with_name(name)  # venv / pipx: misma carpeta bin
    if beside.exists():
        return beside
    found = shutil.which("paste-photo-native-host")
    if found:
        return Path(found)
    raise FileNotFoundError(
        "No se encontró paste-photo-native-host. Reinstala paste-photo (pipx/.deb/instalador)."
    )


def host_manifest(executable: Path) -> dict:
    return {
        "name": protocol.HOST_NAME,
        "description": "paste-photo: pega capturas en claude.ai",
        "path": str(executable),
        "type": "stdio",
        "allowed_origins": [protocol.EXTENSION_ORIGIN],
    }


def install_extension_files(target: Path | None = None) -> Path:
    """Copia la extensión a una carpeta que no cambia entre actualizaciones de la app."""
    target = target or user_data_dir() / "extension"
    shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(resources.path("extension"), target)
    return target


def install_native_host(executable: Path | None = None, home: Path | None = None) -> list[str]:
    """Registra el host nativo para todos los navegadores soportados. Devuelve un informe."""
    manifest = host_manifest(executable or host_executable())
    text = json.dumps(manifest, indent=2)
    if sys.platform == "win32":
        return _install_windows(text)
    return _install_linux(text, home or Path.home())


def _install_linux(text: str, home: Path) -> list[str]:
    config = home / ".config"
    report = []
    for browser, folder in LINUX_BROWSER_DIRS.items():
        browser_dir = config / folder
        # Chrome y Chromium siempre (aunque aún no se hayan abierto); el resto si existen.
        if not browser_dir.exists() and folder not in ("google-chrome", "chromium"):
            continue
        target = browser_dir / "NativeMessagingHosts" / f"{protocol.HOST_NAME}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        report.append(f"{browser}: {target}")
    return report


def _install_windows(text: str) -> list[str]:
    import winreg

    manifest_file = user_data_dir() / "native-host" / f"{protocol.HOST_NAME}.json"
    manifest_file.parent.mkdir(parents=True, exist_ok=True)
    manifest_file.write_text(text, encoding="utf-8")
    report = []
    for browser, key in WINDOWS_REGISTRY_KEYS.items():
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{key}\{protocol.HOST_NAME}") as handle:
            winreg.SetValueEx(handle, "", 0, winreg.REG_SZ, str(manifest_file))
        report.append(f"{browser}: HKCU\\{key}\\{protocol.HOST_NAME}")
    return report


def setup_browser() -> str:
    """Instala todo y devuelve las instrucciones para el usuario."""
    extension = install_extension_files()
    hosts = install_native_host()
    lines = [
        "Host nativo registrado:",
        *[f"  - {line}" for line in hosts],
        "",
        "Falta cargar la extensión (una vez por navegador):",
        "  1. Abre chrome://extensions (edge://extensions, brave://extensions...)",
        "  2. Activa el 'Modo de desarrollador'",
        "  3. 'Cargar descomprimida' y elige esta carpeta:",
        f"     {extension}",
        f"  ID esperado de la extensión: {protocol.EXTENSION_ID}",
        "",
        "Comprueba con: paste-photo doctor",
    ]
    return "\n".join(lines)
