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
    assert [cmd[4] for cmd in sent] == ["term_cerrada", HANDLE]


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
