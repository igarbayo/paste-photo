# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

from paste_photo import config as config_module
from paste_photo.config import ensure_user_config, load_config, save_setting


def test_save_setting_keeps_comments(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text('[general]\n# importante\nprefer = "recent"\n', encoding="utf-8")
    save_setting(path, "general", "prefer", "order")
    save_setting(path, "general", "notify", False)
    text = path.read_text(encoding="utf-8")
    assert "# importante" in text
    cfg = load_config("windows", path)
    assert cfg.prefer == "order"
    assert cfg.notify is False


def test_ensure_user_config_copies_template_once(tmp_path, monkeypatch):
    target = tmp_path / "paste-photo" / "config.toml"
    monkeypatch.setattr(config_module, "user_config_file", lambda: target)
    assert ensure_user_config() == target
    assert "[[targets]]" in target.read_text(encoding="utf-8")
    target.write_text("# mío\n", encoding="utf-8")
    ensure_user_config()
    assert target.read_text(encoding="utf-8") == "# mío\n"  # no se sobrescribe
