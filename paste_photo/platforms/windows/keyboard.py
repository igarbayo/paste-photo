# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Envío de combinaciones de teclas en Windows."""

from __future__ import annotations

import time

import win32api
import win32con

from paste_photo.core.hotkey import parse_hotkey

_MODIFIER_VK = {
    "ctrl": win32con.VK_CONTROL,
    "alt": win32con.VK_MENU,
    "shift": win32con.VK_SHIFT,
    "win": win32con.VK_LWIN,
    "cmd": win32con.VK_LWIN,
}
_NAMED_VK = {
    "enter": win32con.VK_RETURN,
    "tab": win32con.VK_TAB,
    "esc": win32con.VK_ESCAPE,
    "space": win32con.VK_SPACE,
    "insert": win32con.VK_INSERT,
}


def _key_vk(key: str) -> int:
    if key in _NAMED_VK:
        return _NAMED_VK[key]
    if len(key) == 1 and key.isalnum():
        return ord(key.upper())
    raise ValueError(f"Tecla no soportada: {key!r}")


class WindowsKeyboard:
    def __init__(self, key_delay_s: float = 0.02) -> None:
        self._delay = key_delay_s

    def send_hotkey(self, hotkey: str) -> None:
        parsed = parse_hotkey(hotkey)
        mods = [_MODIFIER_VK[m] for m in parsed.modifiers]
        key = _key_vk(parsed.key)
        for vk in mods:
            win32api.keybd_event(vk, 0, 0, 0)
        try:
            time.sleep(self._delay)
            win32api.keybd_event(key, 0, 0, 0)
            time.sleep(self._delay)
            win32api.keybd_event(key, 0, win32con.KEYEVENTF_KEYUP, 0)
        finally:
            for vk in reversed(mods):
                win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)
