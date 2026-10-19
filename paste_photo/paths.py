# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Rutas de usuario por sistema operativo (configuración y registros)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "paste-photo"
CONFIG_FILENAME = "config.toml"
LOG_FILENAME = "paste-photo.log"


def user_config_dir() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / APP_NAME


def user_log_dir() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / APP_NAME / "logs"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Logs" / APP_NAME
    state = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return state / APP_NAME / "logs"


def user_config_file() -> Path:
    return user_config_dir() / CONFIG_FILENAME


def user_log_file() -> Path:
    return user_log_dir() / LOG_FILENAME
