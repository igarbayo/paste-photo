# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Construye los artefactos de distribución (Windows y macOS). Lo usan desarrolladores y CI.

    python packaging/build.py               # .exe (carpeta dist/paste-photo)
    python packaging/build.py --installer   # .exe + instalador (requiere Inno Setup 6)
    python packaging/build.py --dmg         # macOS: PastePhoto.app + .dmg (sin firmar)
    python packaging/build.py --version     # imprime la versión y sale

Una sola fuente de versión: `paste_photo/__init__.py` (`__version__`).
"""

from __future__ import annotations

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
APP_DIR = DIST / "paste-photo"
SPEC = ROOT / "packaging" / "windows" / "paste-photo.spec"
ISS = ROOT / "packaging" / "windows" / "installer.iss"
MAC_SPEC = ROOT / "packaging" / "macos" / "paste-photo.spec"
MAC_APP = DIST / "PastePhoto.app"


def version() -> str:
    text = (ROOT / "paste_photo" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', text)
    if not match:
        raise SystemExit("No se encontró __version__ en paste_photo/__init__.py")
    return match.group(1)


def write_version_info(ver: str) -> Path:
    """Propiedades del .exe (clic derecho > Propiedades > Detalles)."""
    parts = [int(p) for p in re.findall(r"\d+", ver)[:3]] + [0]
    parts += [0] * (4 - len(parts))
    nums = ", ".join(str(p) for p in parts[:4])
    BUILD.mkdir(exist_ok=True)
    target = BUILD / "version_info.txt"
    target.write_text(
        f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers=({nums}), prodvers=({nums})),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'igarbayo'),
      StringStruct('FileDescription', 'PastePhoto'),
      StringStruct('FileVersion', '{ver}'),
      StringStruct('InternalName', 'paste-photo'),
      StringStruct('OriginalFilename', 'paste-photo.exe'),
      StringStruct('ProductName', 'PastePhoto'),
      StringStruct('ProductVersion', '{ver}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""",
        encoding="utf-8",
    )
    return target


def build_exe(ver: str) -> Path:
    write_version_info(ver)
    shutil.rmtree(APP_DIR, ignore_errors=True)
    run([sys.executable, "-m", "PyInstaller", str(SPEC), "--noconfirm", "--clean",
         "--distpath", str(DIST), "--workpath", str(BUILD / "pyinstaller")])
    sys.path.insert(0, str(ROOT / "packaging"))
    from third_party import write_notices

    print(f"OK: {write_notices(APP_DIR)}")
    lgpl_source = APP_DIR / "_internal" / "pystray" / "__init__.py"
    if not lgpl_source.exists():  # requisito LGPL: pystray sustituible por el usuario
        raise SystemExit(f"pystray debe ir como código fuente en {lgpl_source.parent}")
    cli = APP_DIR / "paste-photo-cli.exe"
    # Humo: el .exe arranca, conoce su versión y encuentra los destinos (plugins empaquetados).
    out = run([str(cli), "--version"], capture=True)
    if ver not in out:
        raise SystemExit(f"El .exe no informa la versión esperada {ver}: {out!r}")
    # El host nativo termina limpio cuando el navegador cierra su stdin.
    host = subprocess.run([str(APP_DIR / "paste-photo-native-host.exe"),
                           "chrome-extension://test/"], input=b"", capture_output=True, timeout=30)
    if host.returncode != 0:
        raise SystemExit(f"El host nativo falló: {host.stderr.decode(errors='replace')}")
    targets = run([str(cli), "--list-targets"], capture=True)
    if "windows_terminal" not in targets or "browser" not in targets:
        raise SystemExit(f"Faltan destinos en el .exe: {targets!r}")
    print(f"OK: {APP_DIR}")
    return APP_DIR


def build_app(ver: str) -> Path:
    """macOS: dist/PastePhoto.app (PyInstaller le pone una firma ad hoc, no de desarrollador)."""
    shutil.rmtree(MAC_APP, ignore_errors=True)
    run([sys.executable, str(ROOT / "packaging" / "make_icon.py"), "--icns"])
    os.environ["PASTE_PHOTO_VERSION"] = ver
    run([sys.executable, "-m", "PyInstaller", str(MAC_SPEC), "--noconfirm", "--clean",
         "--distpath", str(DIST), "--workpath", str(BUILD / "pyinstaller")])
    sys.path.insert(0, str(ROOT / "packaging"))
    from third_party import write_notices

    print(f"OK: {write_notices(MAC_APP / 'Contents' / 'Resources')}")
    if not any(MAC_APP.rglob("pystray/__init__.py")):  # requisito LGPL: pystray sustituible
        raise SystemExit("pystray debe ir como código fuente dentro de PastePhoto.app")
    macos = MAC_APP / "Contents" / "MacOS"
    # Humo: el ejecutable arranca, conoce su versión y encuentra los destinos de macOS.
    out = run([str(macos / "paste-photo"), "--version"], capture=True)
    if ver not in out:
        raise SystemExit(f"La app no informa la versión esperada {ver}: {out!r}")
    host = subprocess.run([str(macos / "paste-photo-native-host"), "chrome-extension://test/"],
                          input=b"", capture_output=True, timeout=30)
    if host.returncode != 0:
        raise SystemExit(f"El host nativo falló: {host.stderr.decode(errors='replace')}")
    targets = run([str(macos / "paste-photo"), "--list-targets"], capture=True)
    if "terminal_app" not in targets or "browser_extension" not in targets:
        raise SystemExit(f"Faltan destinos en la app: {targets!r}")
    # Los avisos se añadieron tras la firma ad hoc de PyInstaller: volver a firmar (ad hoc).
    run(["codesign", "--force", "--deep", "--sign", "-", str(MAC_APP)])
    run(["codesign", "--verify", "--deep", "--strict", str(MAC_APP)])
    print(f"OK: {MAC_APP}")
    return MAC_APP


def build_dmg(ver: str) -> Path:
    """Imagen de disco con la app y un acceso a /Applications (arrastrar para instalar)."""
    arch = platform.machine()  # arm64 o x86_64: el .app solo vale para la arquitectura de CI
    dmg = DIST / f"PastePhoto-{ver}-macos-{arch}.dmg"
    stage = BUILD / "dmg"
    shutil.rmtree(stage, ignore_errors=True)
    stage.mkdir(parents=True)
    run(["ditto", str(MAC_APP), str(stage / MAC_APP.name)])  # conserva firma y enlaces
    (stage / "Applications").symlink_to("/Applications")
    dmg.unlink(missing_ok=True)
    run(["hdiutil", "create", "-volname", "PastePhoto", "-srcfolder", str(stage),
         "-format", "UDZO", "-ov", str(dmg)])
    print(f"OK: {dmg}")
    return dmg


def find_iscc() -> Path | None:
    found = shutil.which("iscc") or shutil.which("ISCC")
    if found:
        return Path(found)
    local = os.environ.get("LOCALAPPDATA")
    bases = (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles"),
             local and str(Path(local) / "Programs"))
    for base in bases:
        if base and (candidate := Path(base) / "Inno Setup 6" / "ISCC.exe").exists():
            return candidate
    return None


def build_installer(ver: str) -> Path:
    iscc = find_iscc()
    if iscc is None:
        raise SystemExit("No se encontró Inno Setup 6 (ISCC.exe). Instálalo o usa CI.")
    run([str(iscc), f"/DAppVersion={ver}", f"/DSourceDir={APP_DIR}", f"/DRepoRoot={ROOT}",
         f"/O{DIST}", str(ISS)])
    installer = DIST / f"paste-photo-setup-{ver}.exe"
    if not installer.exists():
        raise SystemExit(f"Inno Setup no generó {installer}")
    print(f"OK: {installer}")
    return installer


def run(cmd: list[str], *, capture: bool = False) -> str:
    print("+", " ".join(cmd), flush=True)
    result = subprocess.run(cmd, check=True, capture_output=capture, text=True, cwd=ROOT)
    return (result.stdout or "") + (result.stderr or "") if capture else ""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--installer", action="store_true", help="crear también el instalador")
    parser.add_argument("--dmg", action="store_true", help="macOS: crear también el .dmg")
    parser.add_argument("--version", action="store_true", help="imprimir la versión y salir")
    args = parser.parse_args()
    ver = version()
    if args.version:
        print(ver)
        return
    if sys.platform == "darwin":
        build_app(ver)
        if args.dmg:
            build_dmg(ver)
        return
    if sys.platform != "win32":
        raise SystemExit("Aquí no hay empaquetado: en Linux, packaging/linux/build_deb.py.")
    build_exe(ver)
    if args.installer:
        build_installer(ver)


if __name__ == "__main__":
    main()
