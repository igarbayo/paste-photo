# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Teclado en macOS: eventos de Quartz (`CGEventPost`). Necesita el permiso de Accesibilidad."""

from __future__ import annotations

import time

from paste_photo.core.hotkey import parse_hotkey

# Códigos de tecla virtuales (posición en un teclado ANSI, `kVK_ANSI_*` de Carbon).
KEYCODES = {
    "a": 0, "s": 1, "d": 2, "f": 3, "h": 4, "g": 5, "z": 6, "x": 7, "c": 8, "v": 9,
    "b": 11, "q": 12, "w": 13, "e": 14, "r": 15, "y": 16, "t": 17, "1": 18, "2": 19,
    "3": 20, "4": 21, "6": 22, "5": 23, "9": 25, "7": 26, "8": 28, "0": 29, "o": 31,
    "u": 32, "i": 34, "p": 35, "l": 37, "j": 38, "k": 40, "n": 45, "m": 46,
    "tab": 48, "space": 49, "escape": 53, "esc": 53,
}
# Modificador → (código de su tecla, bit en las flags del evento: kCGEventFlagMask*).
# "win" es la tecla Windows/Super de un teclado de PC: en macOS hace de Cmd.
MODIFIERS = {
    "cmd": (55, 0x100000),
    "win": (55, 0x100000),
    "shift": (56, 0x020000),
    "alt": (58, 0x080000),
    "ctrl": (59, 0x040000),
}


def key_sequence(hotkey: str) -> list[tuple[int, int, bool]]:
    """`cmd+v` → [(tecla, flags, pulsada), ...]: modificadores, tecla, y se sueltan al revés."""
    parsed = parse_hotkey(hotkey)
    if parsed.key not in KEYCODES:
        raise ValueError(f"Tecla no soportada en macOS: {parsed.key!r}")
    events: list[tuple[int, int, bool]] = []
    flags = 0
    for modifier in parsed.modifiers:
        code, bit = MODIFIERS[modifier]
        flags |= bit
        events.append((code, flags, True))
    code = KEYCODES[parsed.key]
    events += [(code, flags, True), (code, flags, False)]
    for modifier in reversed(parsed.modifiers):
        code, bit = MODIFIERS[modifier]
        flags &= ~bit
        events.append((code, flags, False))
    return events


class MacKeyboard:
    def __init__(self, delay_s: float = 0.01) -> None:
        import Quartz

        self._quartz = Quartz
        self._delay_s = delay_s

    def send_hotkey(self, hotkey: str) -> None:
        from paste_photo.platforms.macos.accessibility import is_trusted

        if not is_trusted():
            raise RuntimeError("falta el permiso de Accesibilidad (Ajustes del Sistema → "
                               "Privacidad y seguridad → Accesibilidad → PastePhoto)")
        q = self._quartz
        # Fuente propia: las flags del evento no se mezclan con las teclas que el usuario
        # tenga pulsadas en ese momento.
        source = q.CGEventSourceCreate(q.kCGEventSourceStatePrivate)
        for code, flags, down in key_sequence(hotkey):
            event = q.CGEventCreateKeyboardEvent(source, code, down)
            q.CGEventSetFlags(event, flags)
            q.CGEventPost(q.kCGHIDEventTap, event)
            time.sleep(self._delay_s)
