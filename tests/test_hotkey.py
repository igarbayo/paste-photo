# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

import pytest

from paste_photo.core.hotkey import Hotkey, parse_hotkey


def test_simple():
    assert parse_hotkey("alt+v") == Hotkey(("alt",), "v")


def test_canonical_order_and_aliases():
    assert parse_hotkey("Shift + Control + V") == Hotkey(("ctrl", "shift"), "v")
    assert parse_hotkey("command+v") == Hotkey(("cmd",), "v")


@pytest.mark.parametrize("bad", ["", "alt+", "alt", "hyper+v"])
def test_invalid(bad):
    with pytest.raises(ValueError):
        parse_hotkey(bad)
