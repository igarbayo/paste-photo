"""Construye los artefactos de distribución. Lo usan tanto los desarrolladores como CI.

    python packaging/build.py               # .exe (carpeta dist/paste-photo)
    python packaging/build.py --installer   # .exe + instalador (requiere Inno Setup 6)
    python packaging/build.py --version     # imprime la versión y sale

Una sola fuente de versión: `paste_photo/__init__.py` (`__version__`).
"""

from __future__ import annotations

import argparse
import os
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
      StringStruct('FileDescription', 'paste-photo'),
      StringStruct('FileVersion', '{ver}'),
      StringStruct('InternalName', 'paste-photo'),
      StringStruct('OriginalFilename', 'paste-photo.exe'),
      StringStruct('ProductName', 'paste-photo'),
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
    cli = APP_DIR / "paste-photo-cli.exe"
    # Humo: el .exe arranca, conoce su versión y encuentra los destinos (plugins empaquetados).
    out = run([str(cli), "--version"], capture=True)
    if ver not in out:
        raise SystemExit(f"El .exe no informa la versión esperada {ver}: {out!r}")
    targets = run([str(cli), "--list-targets"], capture=True)
    if "windows_terminal" not in targets or "browser" not in targets:
        raise SystemExit(f"Faltan destinos en el .exe: {targets!r}")
    print(f"OK: {APP_DIR}")
    return APP_DIR


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
    parser.add_argument("--version", action="store_true", help="imprimir la versión y salir")
    args = parser.parse_args()
    ver = version()
    if args.version:
        print(ver)
        return
    if sys.platform != "win32":
        raise SystemExit("Por ahora solo hay empaquetado para Windows.")
    build_exe(ver)
    if args.installer:
        build_installer(ver)


if __name__ == "__main__":
    main()
