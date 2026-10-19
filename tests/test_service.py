# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

import threading

import pytest

from paste_photo.config import Config
from paste_photo.core.events import NotPasted, Pasted, StateChanged
from paste_photo.service import PasteService
from paste_photo.targets import registry
from tests.fakes import FakeFactory, FakeTarget


@pytest.fixture
def fake_target_type(monkeypatch):
    """Registra un tipo de destino "fake" controlable desde el test."""
    holder = {"window": 10}
    monkeypatch.setitem(
        registry._REGISTRY, "fake", lambda options, ctx: FakeTarget("fake", holder["window"])
    )
    return holder


def make_service(prefer="recent"):
    factory = FakeFactory()
    config = Config(targets=[{"type": "fake"}], prefer=prefer)
    service = PasteService(config, factory)
    events = []
    got = threading.Event()

    def listen(event):
        events.append(event)
        got.set()

    service.subscribe(listen)
    return service, factory, events, got


def test_capture_is_pasted_and_event_emitted(fake_target_type):
    service, factory, events, got = make_service()
    service.start()
    try:
        factory.source.emit("img1")
        assert got.wait(5)
        assert events == [Pasted("img1", "fake", "fake")]
    finally:
        service.stop()
    assert factory.source.stopped


def test_paused_service_ignores_captures(fake_target_type):
    service, factory, events, got = make_service()
    service.start()
    try:
        service.pause()
        assert events == [StateChanged(False)]
        factory.source.emit("img1")
        assert service.probe().result(timeout=5)  # el hilo sigue vivo y responde
        assert events == [StateChanged(False)]
        service.resume()
        assert events[-1] == StateChanged(True)
    finally:
        service.stop()


def test_not_pasted_when_no_claude(fake_target_type):
    fake_target_type["window"] = None
    service, factory, events, got = make_service()
    service.start()
    try:
        factory.source.emit("img1")
        assert got.wait(5)
        assert events == [NotPasted("img1")]
    finally:
        service.stop()


def test_probe_and_set_prefer_run_in_worker(fake_target_type):
    service, factory, events, got = make_service()
    service.start()
    try:
        assert service.probe().result(timeout=5) == [("fake", "fake")]
        service.set_prefer("order").result(timeout=5)
        assert service.submit(lambda o: o.prefer).result(timeout=5) == "order"
        with pytest.raises(ValueError):
            service.set_prefer("nope").result(timeout=5)
    finally:
        service.stop()


def test_startup_error_is_raised_in_start(monkeypatch):
    service, factory, events, got = make_service()  # tipo "fake" sin registrar
    with pytest.raises(ValueError, match="desconocido"):
        service.start()
