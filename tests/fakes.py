# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

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

    def paste(self, handle: TargetHandle, shot=None) -> None:
        if self._focus is not None:
            self._focus.activate(handle.window_id)
        if self._fail_paste:
            raise RuntimeError("boom")
        self.pasted.append(handle)


class FakeSource:
    """Fuente de capturas controlable desde el test (`emit`)."""

    def __init__(self) -> None:
        self.on_capture = None
        self.stopped = False

    def start(self, on_capture) -> None:
        self.on_capture = on_capture

    def stop(self) -> None:
        self.stopped = True

    def emit(self, image_hash: str) -> None:
        from paste_photo.core.events import ScreenshotCaptured

        self.on_capture(ScreenshotCaptured(image_hash=image_hash, timestamp=0.0))


class FakeFactory:
    """Plataforma falsa: permite probar el servicio sin SO."""

    name = "fake"

    def __init__(self) -> None:
        self.source = FakeSource()
        self.focus = FakeFocus()

    def create_screenshot_source(self):
        return self.source

    def create_focus_manager(self):
        return self.focus

    def create_keyboard(self):
        return FakeKeyboard()

    def create_autostart(self):
        raise NotImplementedError

    def create_window_system(self):
        return None

    def worker_context(self):
        from contextlib import nullcontext

        return nullcontext()
