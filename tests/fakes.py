"""Dobles de prueba de los puertos: permiten testear el núcleo en cualquier SO."""

from __future__ import annotations

from dataclasses import dataclass, field

from paste_photo.core.ports import TargetHandle


@dataclass
class FakeFocus:
    current: int = 1
    log: list[str] = field(default_factory=list)

    def capture(self) -> int:
        self.log.append(f"capture:{self.current}")
        return self.current

    def restore(self, snapshot: int) -> None:
        self.log.append(f"restore:{snapshot}")
        self.current = snapshot

    def activate(self, window_id: int) -> None:
        self.log.append(f"activate:{window_id}")
        self.current = window_id


@dataclass
class FakeKeyboard:
    sent: list[str] = field(default_factory=list)

    def send_hotkey(self, hotkey: str) -> None:
        self.sent.append(hotkey)


class FakeTarget:
    def __init__(self, name: str, window_id: int | None, focus: FakeFocus | None = None,
                 fail_locate: bool = False, fail_paste: bool = False) -> None:
        self.name = name
        self._window_id = window_id
        self._focus = focus
        self._fail_locate = fail_locate
        self._fail_paste = fail_paste
        self.pasted: list[TargetHandle] = []

    def locate(self) -> TargetHandle | None:
        if self._fail_locate:
            raise RuntimeError("boom")
        if self._window_id is None:
            return None
        return TargetHandle(window_id=self._window_id, label=self.name)

    def paste(self, handle: TargetHandle) -> None:
        if self._focus is not None:
            self._focus.activate(handle.window_id)
        if self._fail_paste:
            raise RuntimeError("boom")
        self.pasted.append(handle)
