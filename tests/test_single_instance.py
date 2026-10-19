# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

import pytest

from paste_photo import app


def test_second_instance_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(app.tempfile, "gettempdir", lambda: str(tmp_path))
    with app.single_instance():
        with pytest.raises(app.AlreadyRunningError):
            with app.single_instance():
                pass


def test_lock_is_released_on_exit(tmp_path, monkeypatch):
    monkeypatch.setattr(app.tempfile, "gettempdir", lambda: str(tmp_path))
    with app.single_instance():
        pass
    with app.single_instance():
        pass
