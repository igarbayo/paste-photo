# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

r"""Inicio con Windows: valor en HKCU\...\Run (por usuario, sin permisos de administrador).

El instalador escribe y borra el mismo valor, así que el menú de la bandeja y el instalador
ven el mismo estado.
"""

from __future__ import annotations

import winreg

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "paste-photo"


class WindowsAutostart:
    def __init__(self, key_path: str = RUN_KEY, value_name: str = VALUE_NAME) -> None:
        self._key_path = key_path
        self._value_name = value_name

    def is_enabled(self) -> bool:
        return self.command() is not None

    def command(self) -> str | None:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self._key_path) as key:
                value, _type = winreg.QueryValueEx(key, self._value_name)
                return str(value)
        except FileNotFoundError:
            return None

    def enable(self, command: str) -> None:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, self._key_path) as key:
            winreg.SetValueEx(key, self._value_name, 0, winreg.REG_SZ, command)

    def disable(self) -> None:
        try:
            access = winreg.KEY_SET_VALUE
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self._key_path, 0, access) as key:
                winreg.DeleteValue(key, self._value_name)
        except FileNotFoundError:
            pass
