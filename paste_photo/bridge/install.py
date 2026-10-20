# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""`paste-photo setup browser`: registra el host nativo en los navegadores Chromium y Firefox
y deja la extensión en carpetas estables (Chromium: "descomprimida"; Firefox: .xpi)."""

from __future__ import annotations

import json
import shutil
import sys
import zipfile
from pathlib import Path

from paste_photo import resources
from paste_photo.bridge import protocol
from paste_photo.paths import user_data_dir

# Linux: carpetas de configuración de cada navegador Chromium (en ~/.config).
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
# Linux: carpetas de la familia Firefox (en ~); el host va en `native-messaging-hosts`.
LINUX_GECKO_DIRS = {
    "Firefox": ".mozilla",
    "LibreWolf": ".librewolf",
}
# Windows: claves de registro (HKCU) donde cada navegador Chromium busca hosts nativos.
WINDOWS_REGISTRY_KEYS = {
    "Google Chrome": r"Software\Google\Chrome\NativeMessagingHosts",
    "Chromium": r"Software\Chromium\NativeMessagingHosts",
    "Microsoft Edge": r"Software\Microsoft\Edge\NativeMessagingHosts",
    "Brave": r"Software\BraveSoftware\Brave-Browser\NativeMessagingHosts",
    "Vivaldi": r"Software\Vivaldi\NativeMessagingHosts",
}
# Windows: las mismas claves para la familia Firefox.
WINDOWS_GECKO_KEYS = {
    "Firefox": r"Software\Mozilla\NativeMessagingHosts",
    "LibreWolf": r"Software\LibreWolf\NativeMessagingHosts",
}
# Versión mínima: `background.scripts` junto a `service_worker` (121) en la ESR actual.
FIREFOX_MIN_VERSION = "128.0"


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


def host_manifest(executable: Path, *, gecko: bool = False) -> dict:
    """Manifiesto del host: Chromium autoriza por origen, Firefox por ID de la extensión."""
    manifest = {
        "name": protocol.HOST_NAME,
        "description": "paste-photo: pega capturas en claude.ai",
        "path": str(executable),
        "type": "stdio",
    }
    if gecko:
        manifest["allowed_extensions"] = [protocol.FIREFOX_EXTENSION_ID]
    else:
        manifest["allowed_origins"] = [protocol.EXTENSION_ORIGIN]
    return manifest


def firefox_manifest(chromium: dict) -> dict:
    """La extensión de Firefox sale de la de Chromium: Firefox no tiene service workers en
    las extensiones (usa `background.scripts`), su ID va en `browser_specific_settings` y
    no entiende `key`."""
    manifest = {k: v for k, v in chromium.items() if k != "key"}
    manifest["background"] = {"scripts": [chromium["background"]["service_worker"]]}
    manifest["browser_specific_settings"] = {
        "gecko": {
            "id": protocol.FIREFOX_EXTENSION_ID,
            "strict_min_version": FIREFOX_MIN_VERSION,
            "data_collection_permissions": {"required": ["none"]},
        }
    }
    return manifest


def install_extension_files(target: Path | None = None) -> Path:
    """Copia la extensión a una carpeta que no cambia entre actualizaciones de la app."""
    target = target or user_data_dir() / "extension"
    shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(resources.path("extension"), target)
    return target


def build_firefox_extension(target: Path) -> Path:
    """Escribe la extensión de Firefox en `target` (carpeta) y `target`.xpi. Devuelve el .xpi."""
    shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(resources.path("extension"), target)
    chromium = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    (target / "manifest.json").write_text(
        json.dumps(firefox_manifest(chromium), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    xpi = target.with_suffix(".xpi")
    with zipfile.ZipFile(xpi, "w", zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(p for p in target.rglob("*") if p.is_file()):
            archive.write(file, file.relative_to(target).as_posix())
    return xpi


def linux_host_manifests(home: Path) -> dict[str, tuple[Path, bool]]:
    """navegador → (ruta del manifiesto del host, es Firefox)."""
    found = {browser: (home / ".config" / folder / "NativeMessagingHosts", False)
             for browser, folder in LINUX_BROWSER_DIRS.items()}
    found |= {browser: (home / folder / "native-messaging-hosts", True)
              for browser, folder in LINUX_GECKO_DIRS.items()}
    return {browser: (folder / f"{protocol.HOST_NAME}.json", gecko)
            for browser, (folder, gecko) in found.items()}


def windows_host_keys() -> dict[str, tuple[str, bool]]:
    """navegador → (clave de HKCU del host, es Firefox)."""
    keys = {browser: (key, False) for browser, key in WINDOWS_REGISTRY_KEYS.items()}
    keys |= {browser: (key, True) for browser, key in WINDOWS_GECKO_KEYS.items()}
    return {browser: (rf"{key}\{protocol.HOST_NAME}", gecko)
            for browser, (key, gecko) in keys.items()}


def install_native_host(executable: Path | None = None, home: Path | None = None) -> list[str]:
    """Registra el host nativo para todos los navegadores soportados. Devuelve un informe."""
    executable = executable or host_executable()
    texts = {gecko: json.dumps(host_manifest(executable, gecko=gecko), indent=2)
             for gecko in (False, True)}
    if sys.platform == "win32":
        return _install_windows(texts)
    return _install_linux(texts, home or Path.home())


def _install_linux(texts: dict[bool, str], home: Path) -> list[str]:
    report = []
    for browser, (target, gecko) in linux_host_manifests(home).items():
        # La carpeta del navegador (~/.config/chromium, ~/.mozilla...) debe existir, salvo en
        # Chrome, Chromium y Firefox, que se registran aunque aún no se hayan abierto.
        if not target.parent.parent.exists() and browser not in (
                "Google Chrome", "Chromium", "Firefox"):
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(texts[gecko], encoding="utf-8")
        report.append(f"{browser}: {target}")
    return report


def _install_windows(texts: dict[bool, str]) -> list[str]:
    import winreg

    folder = user_data_dir() / "native-host"
    folder.mkdir(parents=True, exist_ok=True)
    files = {gecko: folder / f"{protocol.HOST_NAME}{'.firefox' if gecko else ''}.json"
             for gecko in (False, True)}
    for gecko, file in files.items():
        file.write_text(texts[gecko], encoding="utf-8")
    report = []
    for browser, (key, gecko) in windows_host_keys().items():
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key) as handle:
            winreg.SetValueEx(handle, "", 0, winreg.REG_SZ, str(files[gecko]))
        report.append(f"{browser}: HKCU\\{key}")
    return report


def setup_browser() -> str:
    """Instala todo y devuelve las instrucciones para el usuario."""
    extension = install_extension_files()
    xpi = build_firefox_extension(user_data_dir() / "extension-firefox")
    hosts = install_native_host()
    lines = [
        "Host nativo registrado:",
        *[f"  - {line}" for line in hosts],
        "",
        "Chrome, Edge, Brave, Vivaldi, Opera... (una vez por navegador):",
        "  1. Abre chrome://extensions (edge://extensions, brave://extensions...)",
        "  2. Activa el 'Modo de desarrollador'",
        "  3. 'Cargar descomprimida' y elige esta carpeta:",
        f"     {extension}",
        f"  ID esperado de la extensión: {protocol.EXTENSION_ID}",
        "",
        "Firefox, LibreWolf...:",
        "  - Instala el .xpi firmado de la página de versiones de paste-photo, o",
        "  - sin firmar (Firefox ESR, Developer Edition, Nightly, LibreWolf, con",
        "    xpinstall.signatures.required = false en about:config): about:addons →",
        "    ⚙ → 'Instalar complemento desde archivo' y elige:",
        f"     {xpi}",
        "",
        "Comprueba con: paste-photo doctor",
    ]
    return "\n".join(lines)
