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
    with pytest.raises(NotImplementedError, match="browser"):
        build_target({"type": "browser"}, ctx())


def test_windows_terminal_rejects_other_platforms():
    with pytest.raises(ValueError, match="Windows"):
        build_target({"type": "windows_terminal"}, ctx("macos"))


def test_config_defaults_when_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("paste_photo.config.user_config_dir", lambda: tmp_path / "none")
    cfg = load_config("windows")
    assert cfg.source is None
    assert cfg.targets == [{"type": "windows_terminal"}]


def test_config_from_file_skips_disabled(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        '[general]\ndebounce_ms = 500\nrestore_focus = false\n'
        '[[targets]]\ntype = "browser"\nenabled = false\n'
        '[[targets]]\ntype = "windows_terminal"\ntitle_regex = "foo"\n',
        encoding="utf-8",
    )
    cfg = load_config("windows", path)
    assert cfg.debounce_ms == 500
    assert cfg.restore_focus is False
    assert cfg.targets == [{"type": "windows_terminal", "title_regex": "foo"}]


def test_shipped_config_parses():
    from pathlib import Path

    cfg = load_config("windows", Path(__file__).parent.parent / "config.toml")
    assert cfg.targets[0]["type"] == "windows_terminal"
