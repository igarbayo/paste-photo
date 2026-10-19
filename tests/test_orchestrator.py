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


def test_same_image_is_pasted_only_once_even_much_later():
    # Bug real: el usuario quitaba la imagen y otra app la devolvía al portapapeles
    # minutos después; se volvía a pegar.
    target = FakeTarget("t", 10)
    orch = Orchestrator([target], FakeFocus())

    orch.handle(shot("same", 0.0))
    orch.handle(shot("same", 1.0))
    orch.handle(shot("same", 600.0))

    assert len(target.pasted) == 1


def test_image_memory_is_bounded():
    target = FakeTarget("t", 10)
    orch = Orchestrator([target], FakeFocus(), remember_images=2)

    for h in ("a", "b", "c"):  # "a" sale de la memoria
        orch.handle(shot(h))
    orch.handle(shot("a"))
    orch.handle(shot("c"))  # sigue recordada

    assert [p.label for p in target.pasted] == ["t"] * 4


def test_failed_paste_falls_through_to_next_target():
    good = FakeTarget("good", 20)
    orch = Orchestrator([FakeTarget("bad", 10, fail_paste=True), good], FakeFocus())

    assert orch.handle(shot()) == "good"


def test_failed_image_is_not_retried():
    # Si no se pudo pegar en ningún sitio, la misma imagen no se reintenta sola.
    target = FakeTarget("t", None)
    orch = Orchestrator([target], FakeFocus())

    assert orch.handle(shot("x")) is None
    assert orch.handle(shot("x")) is None


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


def test_recent_prefers_last_used_window_over_config_order():
    # Caso real: terminal y navegador abiertos; el usuario está en la terminal.
    from paste_photo.core.recency import Recency

    recency = Recency()
    browser = FakeTarget("browser", 20)
    terminal = FakeTarget("terminal", 10)
    orch = Orchestrator([browser, terminal], FakeFocus(), recency=recency)

    recency.touch(20, at=1.0)   # usó el navegador hace un rato
    recency.touch(10, at=5.0)   # y ahora está en la terminal
    assert orch.handle(shot("a")) == "terminal"

    recency.touch(20, at=9.0)   # vuelve al navegador
    assert orch.handle(shot("b")) == "browser"


def test_recent_falls_back_to_config_order_without_history():
    orch = Orchestrator([FakeTarget("first", 1), FakeTarget("second", 2)], FakeFocus())
    assert orch.handle(shot()) == "first"


def test_order_mode_ignores_recency():
    from paste_photo.core.recency import Recency

    recency = Recency()
    recency.touch(2, at=10.0)
    orch = Orchestrator(
        [FakeTarget("first", 1), FakeTarget("second", 2)], FakeFocus(), recency=recency,
        prefer="order",
    )
    assert orch.handle(shot()) == "first"


def test_invalid_prefer():
    import pytest

    with pytest.raises(ValueError):
        Orchestrator([], FakeFocus(), prefer="random")
