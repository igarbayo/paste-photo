# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Scripts de empaquetado: los usa CI al publicar, así que un fallo rompería la release."""

import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def load(relative: str):
    spec = importlib.util.spec_from_file_location(Path(relative).stem, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_version_matches_package():
    from paste_photo import __version__

    assert load("packaging/build.py").version() == __version__


def test_current_version_has_changelog_section():
    from paste_photo import __version__

    notes = load("packaging/release_notes.py")
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert notes.notes(__version__, text).strip()


def test_release_notes_extracts_only_that_version():
    notes = load("packaging/release_notes.py")
    text = "## [Unreleased]\n\n## [1.1.0] - 2026-01-02\n### Added\n- b\n\n## [1.0.0]\n- a\n"
    assert notes.notes("1.1.0", text) == "### Added\n- b\n"
    with pytest.raises(SystemExit):
        notes.notes("9.9.9", text)


def test_winget_manifests(tmp_path):
    winget = load("packaging/winget/make_manifests.py")
    folder = winget.write("1.2.3", "https://example.com/setup.exe", "ab" * 32, tmp_path)
    assert folder == tmp_path / "manifests" / "i" / "igarbayo" / "paste-photo" / "1.2.3"
    files = sorted(p.name for p in folder.iterdir())
    assert files == [
        "igarbayo.paste-photo.installer.yaml",
        "igarbayo.paste-photo.locale.en-US.yaml",
        "igarbayo.paste-photo.yaml",
    ]
    installer = (folder / "igarbayo.paste-photo.installer.yaml").read_text(encoding="utf-8")
    assert "InstallerSha256: " + "AB" * 32 in installer
    assert "InstallerType: inno" in installer and "Scope: user" in installer
    locale = (folder / "igarbayo.paste-photo.locale.en-US.yaml").read_text(encoding="utf-8")
    assert "License: MIT" in locale
    for path in folder.iterdir():
        assert re.search(r"^PackageVersion: 1\.2\.3$", path.read_text(encoding="utf-8"), re.M)


def test_third_party_notices(tmp_path):
    third_party = load("packaging/third_party.py")
    names = {d.metadata["Name"].lower() for d in third_party.runtime_distributions()}
    assert {"pystray", "pillow", "tomlkit", "psutil"} <= names
    assert "pytest" not in names and "pyinstaller" not in names  # solo dependencias de ejecución
    notices = third_party.write_notices(tmp_path)
    text = notices.read_text(encoding="utf-8")
    assert "MIT License" in (tmp_path / "LICENSE").read_text(encoding="utf-8")
    assert "LGPL" in text and "_internal/pystray" in text
    assert (tmp_path / "licenses" / "pystray" / "COPYING.LGPL").exists()


def test_project_license_is_mit():
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert text.startswith("MIT License") and "2026 igarbayo" in text
    assert (ROOT / "LICENSES" / "MIT.txt").read_text(encoding="utf-8") == text
