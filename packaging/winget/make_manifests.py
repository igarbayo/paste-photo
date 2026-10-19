"""Genera los manifiestos de winget para una versión publicada.

    python packaging/winget/make_manifests.py --version 0.2.0 --sha256 <hash> --out dist/winget \
        --url https://github.com/igarbayo/paste-photo/releases/download/v0.2.0/paste-photo-setup-0.2.0.exe

Escribe la estructura que espera el repositorio microsoft/winget-pkgs:
    <out>/manifests/i/igarbayo/paste-photo/<versión>/*.yaml
Validar en local: winget validate --manifest <carpeta de la versión>
"""

from __future__ import annotations

import argparse
from pathlib import Path

PACKAGE_ID = "igarbayo.paste-photo"
MANIFEST_VERSION = "1.6.0"
SCHEMA = "https://aka.ms/winget-manifest.{kind}.{v}.schema.json"
HEADER = "# yaml-language-server: $schema={schema}\n"


def manifests(version: str, url: str, sha256: str) -> dict[str, str]:
    base = f"PackageIdentifier: {PACKAGE_ID}\nPackageVersion: {version}\n"
    return {
        f"{PACKAGE_ID}.yaml": _doc("version", base + (
            "DefaultLocale: en-US\n"
            "ManifestType: version\n"
        )),
        f"{PACKAGE_ID}.installer.yaml": _doc("installer", base + (
            "InstallerType: inno\n"
            "Scope: user\n"
            "InstallModes:\n  - interactive\n  - silent\n  - silentWithProgress\n"
            "UpgradeBehavior: install\n"
            "Commands:\n  - paste-photo-cli\n"
            "Installers:\n"
            "  - Architecture: x64\n"
            f"    InstallerUrl: {url}\n"
            f"    InstallerSha256: {sha256.upper()}\n"
            "ManifestType: installer\n"
        )),
        f"{PACKAGE_ID}.locale.en-US.yaml": _doc("defaultLocale", base + (
            "PackageLocale: en-US\n"
            "Publisher: igarbayo\n"
            "PublisherUrl: https://github.com/igarbayo\n"
            "PackageName: paste-photo\n"
            "PackageUrl: https://github.com/igarbayo/paste-photo\n"
            "License: Proprietary\n"
            "ShortDescription: Automatically paste your screenshots into Claude.\n"
            "Description: |-\n"
            "  Take a screenshot and it shows up in Claude by itself: Claude Code in Windows\n"
            "  Terminal or any claude.ai chat in Chrome/Edge. Runs in the system tray.\n"
            "Tags:\n  - claude\n  - screenshot\n  - clipboard\n  - productivity\n"
            "ReleaseNotesUrl: https://github.com/igarbayo/paste-photo/blob/main/CHANGELOG.md\n"
            "ManifestType: defaultLocale\n"
        )),
    }


def _doc(kind: str, body: str) -> str:
    schema = SCHEMA.format(kind=kind, v=MANIFEST_VERSION)
    return HEADER.format(schema=schema) + body + f"ManifestVersion: {MANIFEST_VERSION}\n"


def write(version: str, url: str, sha256: str, out: Path) -> Path:
    folder = out / "manifests" / PACKAGE_ID[0].lower() / "igarbayo" / "paste-photo" / version
    folder.mkdir(parents=True, exist_ok=True)
    for name, content in manifests(version, url, sha256).items():
        (folder / name).write_text(content, encoding="utf-8", newline="\n")
    return folder


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--out", type=Path, default=Path("dist/winget"))
    args = parser.parse_args()
    print(write(args.version, args.url, args.sha256, args.out))


if __name__ == "__main__":
    main()
