# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Registro de qué ventanas ha usado el usuario y cuándo (para elegir el Claude más reciente)."""

from __future__ import annotations

import time
from collections import OrderedDict
from collections.abc import Callable

NEVER = float("-inf")


class Recency:
    """Instante en que cada ventana tuvo el foco por última vez. No es thread-safe:
    se usa desde el hilo principal."""

    def __init__(self, clock: Callable[[], float] = time.monotonic, max_windows: int = 500):
        self._clock = clock
        self._max = max_windows
        self._seen: OrderedDict[int, float] = OrderedDict()

    def touch(self, window_id: int, at: float | None = None) -> None:
        if not window_id:
            return
        self._seen[window_id] = self._clock() if at is None else at
        self._seen.move_to_end(window_id)
        while len(self._seen) > self._max:
            self._seen.popitem(last=False)

    def last_seen(self, window_id: int) -> float:
        return self._seen.get(window_id, NEVER)
