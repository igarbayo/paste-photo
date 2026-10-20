# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

import pytest

from paste_photo.config import load_config
from paste_photo.targets import TargetContext, available_targets, build_target
from tests.fakes import FakeFocus, FakeKeyboard


def ctx(platform: str = "linux") -> TargetContext:
    return TargetContext(platform=platform, focus=FakeFocus(), keyboard=FakeKeyboard())


def test_builtin_targets_are_registered():
    assert {"windows_terminal", "desktop_app", "browser", "vscode"} <= set(available_targets())


def test_unknown_target_type():
    with pytest.raises(ValueError, match="desconocido"):
        build_target({"type": "nope"}, ctx())


def test_pending_target_fails_with_clear_message():
    with pytest.raises(NotImplementedError, match="desktop_app"):
        build_target({"type": "desktop_app"}, ctx())


def test_windows_terminal_rejects_other_platforms():
    with pytest.raises(ValueError, match="no funciona en macos"):
        build_target({"type": "windows_terminal"}, ctx("macos"))


def test_targets_declare_their_platforms():
    from paste_photo.targets import supports

    assert supports("windows_terminal", "windows") and not supports("windows_terminal", "linux")
    assert supports("tmux", "linux") and not supports("tmux", "windows")
    assert supports("browser_extension", "linux") and supports("browser_extension", "windows")


def test_service_skips_targets_of_other_platforms():
    from paste_photo.config import Config
    from paste_photo.service import build_targets

    config = Config(targets=[{"type": "windows_terminal"}, {"type": "tmux"},
                             {"type": "browser_extension"}])
    names = [t.name for t in build_targets(config, ctx("linux"))]
    assert names == ["tmux", "browser_extension"]


def test_config_defaults_when_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("paste_photo.config.user_config_dir", lambda: tmp_path / "none")
    cfg = load_config("windows")
    assert cfg.source is None
    assert [t["type"] for t in cfg.targets] == [
        "browser_extension", "orca", "windows_terminal", "browser", "tmux", "kitty", "wezterm",
        "konsole", "iterm2", "terminal_app", "macos_terminal", "macos_browser",
        "linux_terminal", "linux_browser"]


def test_config_from_file_skips_disabled(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        '[general]\nremember_images = 5\nrestore_focus = false\n'
        '[[targets]]\ntype = "browser"\nenabled = false\n'
        '[[targets]]\ntype = "windows_terminal"\ntitle_regex = "foo"\n',
        encoding="utf-8",
    )
    cfg = load_config("windows", path)
    assert cfg.remember_images == 5
    assert cfg.restore_focus is False
    assert cfg.targets == [{"type": "windows_terminal", "title_regex": "foo"}]


def test_shipped_config_parses():
    from pathlib import Path

    shipped = Path(__file__).parent.parent / "paste_photo" / "resources" / "default_config.toml"
    cfg = load_config("windows", shipped)
    assert cfg.targets[0]["type"] == "browser_extension"
    from paste_photo.targets import available_targets

    assert {t["type"] for t in cfg.targets} <= set(available_targets())
