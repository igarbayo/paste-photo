from paste_photo.core.events import ScreenshotCaptured
from paste_photo.core.orchestrator import Orchestrator
from tests.fakes import FakeFocus, FakeTarget


def shot(h: str = "abc", t: float = 0.0) -> ScreenshotCaptured:
    return ScreenshotCaptured(image_hash=h, timestamp=t)


def test_first_matching_target_wins():
    focus = FakeFocus()
    absent = FakeTarget("absent", None)
    first = FakeTarget("first", 10)
    second = FakeTarget("second", 20)
    orch = Orchestrator([absent, first, second], focus)

    assert orch.handle(shot()) == "first"
    assert len(first.pasted) == 1
    assert second.pasted == []


def test_no_target_found_is_noop():
    orch = Orchestrator([FakeTarget("absent", None)], FakeFocus())
    assert orch.handle(shot()) is None


def test_duplicate_within_debounce_is_ignored():
    target = FakeTarget("t", 10)
    orch = Orchestrator([target], FakeFocus(), debounce_s=2.0)

    orch.handle(shot("same", 0.0))
    orch.handle(shot("same", 1.0))
    orch.handle(shot("same", 2.5))  # fuera de la ventana: vuelve a pegarse

    assert len(target.pasted) == 2


def test_different_images_are_both_pasted():
    target = FakeTarget("t", 10)
    orch = Orchestrator([target], FakeFocus())

    orch.handle(shot("a", 0.0))
    orch.handle(shot("b", 0.1))

    assert len(target.pasted) == 2


def test_focus_is_restored_after_paste():
    focus = FakeFocus(current=1)
    orch = Orchestrator([FakeTarget("t", 10, focus=focus)], focus)

    orch.handle(shot())

    assert focus.log == ["capture:1", "activate:10", "restore:1"]
    assert focus.current == 1


def test_focus_is_restored_even_if_paste_fails():
    focus = FakeFocus(current=1)
    orch = Orchestrator([FakeTarget("t", 10, focus=focus, fail_paste=True)], focus)

    assert orch.handle(shot()) is None
    assert focus.current == 1


def test_restore_focus_disabled():
    focus = FakeFocus(current=1)
    orch = Orchestrator([FakeTarget("t", 10, focus=focus)], focus, restore_focus=False)

    orch.handle(shot())

    assert focus.current == 10


def test_failing_locate_falls_through_to_next_target():
    good = FakeTarget("good", 10)
    orch = Orchestrator([FakeTarget("bad", 1, fail_locate=True), good], FakeFocus())

    assert orch.handle(shot()) == "good"
