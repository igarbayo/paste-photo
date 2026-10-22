# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Destino Orca: terminal por `ORCA_TERMINAL_HANDLE`, tecla de pegado por SO y CLI."""

import pytest

from paste_photo.core.ports import WindowInfo
from paste_photo.core.recency import Recency
from paste_photo.targets import orca
from paste_photo.targets._env_terminal import handled_by_ipc
from paste_photo.targets._processes import ClaudeProcess
from paste_photo.targets.registry import TargetContext
from tests.fakes import FakeFocus, FakeKeyboard

# Handle real observado en Orca 1.4.224 (Windows).
HANDLE = "term_d5dcd8b7-3baa-4358-89b8-bda226f0f7e6"


def ctx(platform="linux", windows=None, recency=None) -> TargetContext:
    return TargetContext(platform=platform, focus=FakeFocus(), keyboard=FakeKeyboard(),
                         recency=recency or Recency(), windows=windows)


def claude(pid, **env) -> ClaudeProcess:
    return ClaudeProcess(pid, dict(env), (100,))


@pytest.fixture
def procs(monkeypatch):
    found: list[ClaudeProcess] = []
    monkeypatch.setattr("paste_photo.targets._env_terminal.claude_processes",
                        lambda: list(found))
    return found


@pytest.fixture
def sent(monkeypatch):
    calls: list[list[str]] = []

    def fake_run(cmd, env=None):
        calls.append(list(cmd))
        if "term_cerrada" in cmd:
            raise RuntimeError("terminal_handle_stale")
        return '{"ok": true}'

    monkeypatch.setattr(orca, "run", fake_run)
    return calls


def test_locates_claude_by_terminal_handle(procs):
    procs += [claude(1, ORCA_TERMINAL_HANDLE=HANDLE), claude(2, WEZTERM_PANE="0")]
    handle = orca.OrcaTarget(ctx(), cli="orca").locate()
    assert handle.label == f"Orca {HANDLE}"
    assert [c.extra["proc"].pid for c in handle.extra["candidates"]] == [1]


def test_tmux_inside_orca_is_left_to_tmux(procs):
    procs.append(claude(1, ORCA_TERMINAL_HANDLE=HANDLE, TMUX="/tmp/tmux-1000/default,5,0",
                        TMUX_PANE="%1"))
    assert orca.OrcaTarget(ctx(), cli="orca").locate() is None


def test_linux_terminal_ignores_orca():
    assert handled_by_ipc({"ORCA_TERMINAL_HANDLE": HANDLE})


@pytest.mark.parametrize(("platform", "text"), [("windows", "\x1bv"), ("linux", "\x16")])
def test_sends_paste_key_of_each_os_without_enter(procs, sent, platform, text):
    procs.append(claude(1, ORCA_TERMINAL_HANDLE=HANDLE))
    target = orca.OrcaTarget(ctx(platform), cli="orca")
    target._list_windows = lambda: []  # sin escritorio en los tests
    target.paste(target.locate())
    assert sent == [["orca", "terminal", "send", "--terminal", HANDLE, "--text", text, "--json"]]
    assert "--enter" not in sent[0]


def test_falls_back_to_next_terminal(procs, sent):
    procs += [claude(1, ORCA_TERMINAL_HANDLE="term_cerrada"),
              claude(2, ORCA_TERMINAL_HANDLE=HANDLE)]
    target = orca.OrcaTarget(ctx(), cli="orca", paste_text="\x16")
    target.paste(target.locate())
    assert [cmd[4] for cmd in sent if "send" in cmd] == ["term_cerrada", HANDLE]


def test_uses_most_recent_orca_window(procs, monkeypatch):
    class Windows:
        def list_windows(self):
            return [WindowInfo(10, "Orca", 500), WindowInfo(20, "Orca", 500),
                    WindowInfo(30, "✳ otra terminal", 600)]

    monkeypatch.setattr(orca, "process_name", lambda pid: "orca-ide" if pid == 500 else "xterm")
    recency = Recency(clock=lambda: 0)
    recency.touch(10, at=1)
    recency.touch(20, at=2)
    procs.append(claude(1, ORCA_TERMINAL_HANDLE=HANDLE))
    handle = orca.OrcaTarget(ctx(windows=Windows(), recency=recency), cli="orca").locate()
    assert handle.window_id == 20  # los PTY cuelgan del daemon: la ventana más reciente


def test_cli_from_terminal_path(monkeypatch, tmp_path):
    monkeypatch.setattr(orca.shutil, "which",
                        lambda exe, path=None: f"{path}/{exe}" if path else None)
    proc = claude(1, ORCA_TERMINAL_HANDLE=HANDLE, PATH=str(tmp_path))
    assert orca.OrcaTarget(ctx()).cli_for(proc).startswith(str(tmp_path))


def test_cli_missing_is_an_error(monkeypatch):
    monkeypatch.setattr(orca.shutil, "which", lambda exe, path=None: None)
    monkeypatch.setattr(orca, "known_cli_paths", lambda: [])
    with pytest.raises(RuntimeError):
        orca.OrcaTarget(ctx()).cli_for(claude(1, ORCA_TERMINAL_HANDLE=HANDLE))


def layouts(active_tab, *tabs, active_leaf=None):
    """Topología como la de `orca terminal list --include-visual-layouts` (Orca 1.4.237)."""
    return {"ok": True, "result": {"terminals": [], "visualLayouts": [{"root": {
        "type": "group", "activeTabId": active_tab, "tabs": [
            {"tabId": tab, "activeLeafId": active_leaf or f"leaf-{handle}",
             "panes": {"type": "terminal", "handle": handle, "leafId": f"leaf-{handle}"}}
            for tab, handle in tabs]}}]}}


def test_prefers_selected_tab_over_busy_one(procs, monkeypatch):
    # Dos Claude en la misma ventana de Orca: gana la pestaña seleccionada, no la primera.
    import json
    monkeypatch.setattr(orca, "run", lambda cmd, env=None: json.dumps(
        layouts("tab-b", ("tab-a", "term_a"), ("tab-b", "term_b"))))
    procs += [claude(1, ORCA_TERMINAL_HANDLE="term_a"), claude(2, ORCA_TERMINAL_HANDLE="term_b")]
    target = orca.OrcaTarget(ctx(), cli="orca")
    target._list_windows = lambda: []
    handle = target.locate()
    assert [c.extra["proc"].pid for c in handle.extra["candidates"]] == [2, 1]


def test_active_pane_of_split_tab_wins(procs, monkeypatch):
    import json
    data = {"ok": True, "result": {"visualLayouts": [{"root": {
        "type": "group", "activeTabId": "tab", "tabs": [{
            "tabId": "tab", "activeLeafId": "leaf-b", "panes": {"type": "split", "children": [
                {"type": "terminal", "handle": "term_a", "leafId": "leaf-a"},
                {"type": "terminal", "handle": "term_b", "leafId": "leaf-b"}]}}]}}]}}
    monkeypatch.setattr(orca, "run", lambda cmd, env=None: json.dumps(data))
    procs += [claude(1, ORCA_TERMINAL_HANDLE="term_a"), claude(2, ORCA_TERMINAL_HANDLE="term_b")]
    target = orca.OrcaTarget(ctx(), cli="orca")
    assert target.session_rank(list(procs)) == {1: (0, 1), 2: (0, 0)}


def test_no_rank_query_with_single_claude_or_failing_cli(procs, monkeypatch):
    calls = []

    def failing(cmd, env=None):
        calls.append(cmd)
        raise RuntimeError("orca falló (1)")

    monkeypatch.setattr(orca, "run", failing)
    target = orca.OrcaTarget(ctx(), cli="orca")
    one = [claude(1, ORCA_TERMINAL_HANDLE="term_a")]
    assert target.session_rank(one) == {} and calls == []
    assert target.session_rank(one + [claude(2, ORCA_TERMINAL_HANDLE="term_b")]) == {}
