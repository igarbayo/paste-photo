# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Lógica de macOS que no necesita un Mac: teclas, portapapeles, capturas, LaunchAgent,
manifiestos del host y elección de destino (iTerm2, Terminal, otros terminales, navegadores)."""

import json
import plistlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from paste_photo.core.ports import WindowInfo
from paste_photo.targets._processes import ClaudeProcess
from paste_photo.targets.registry import TargetContext
from tests.fakes import FakeFocus, FakeKeyboard


class FakeWindows:
    def __init__(self, windows):
        self.windows, self.activated = windows, []

    def list_windows(self):
        return self.windows

    def active_window(self):
        return None

    def activate(self, window_id):
        self.activated.append(window_id)


def ctx(windows=None) -> TargetContext:
    return TargetContext(platform="macos", focus=FakeFocus(), keyboard=FakeKeyboard(),
                         windows=windows)


def claude(pid, ancestors=(100,), **env) -> ClaudeProcess:
    return ClaudeProcess(pid, dict(env), tuple(ancestors))


@pytest.fixture
def procs(monkeypatch):
    found: list[ClaudeProcess] = []
    for module in ("paste_photo.targets._env_terminal", "paste_photo.targets.macos_terminal"):
        monkeypatch.setattr(f"{module}.claude_processes", lambda: list(found))
    return found


# --- teclado, portapapeles, capturas --------------------------------------------------------


def test_key_sequence():
    from paste_photo.platforms.macos.keyboard import key_sequence

    assert key_sequence("cmd+v") == [(55, 0x100000, True), (9, 0x100000, True),
                                     (9, 0x100000, False), (55, 0, False)]
    ctrl_shift = key_sequence("ctrl+shift+v")
    assert ctrl_shift[2] == (9, 0x040000 | 0x020000, True) and ctrl_shift[-1][1] == 0
    with pytest.raises(ValueError):
        key_sequence("ctrl+f13")


def test_pick_pasteboard_type():
    from paste_photo.platforms.macos.sources import pick_pasteboard_type

    assert pick_pasteboard_type(["public.tiff", "public.png"]) == "public.png"
    assert pick_pasteboard_type(["public.tiff"]) == "public.tiff"
    assert pick_pasteboard_type(["public.utf8-plain-text"]) is None
    # Archivos copiados en el Finder: la imagen es su icono.
    assert pick_pasteboard_type(["public.file-url", "public.tiff"]) is None


def test_is_screenshot_file():
    from paste_photo.platforms.macos.sources import SCREENSHOT_PREFIXES, is_screenshot_file

    def check(name):
        return is_screenshot_file(Path(name), SCREENSHOT_PREFIXES)

    assert check("Captura de pantalla 2026-10-20 a las 10.15.02.png")
    assert check("Screenshot 2026-10-20 at 10.15.02.png")
    assert not check(".Captura de pantalla 2026-10-20 a las 10.15.02.png")  # aún escribiéndose
    assert not check("vacaciones.png")
    assert not check("Screenshot notas.txt")
    assert is_screenshot_file(Path("Mi captura 1.png"), ("Mi captura",))


def test_screenshot_folders_reads_location_last(tmp_path, monkeypatch):
    from paste_photo.platforms.macos.sources import screenshot_folders

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    for var in ("HOME", "USERPROFILE"):  # los que lee expanduser("~/...")
        monkeypatch.setenv(var, str(tmp_path))
    desktop, shots = tmp_path / "Desktop", tmp_path / "Desktop" / "Screenshots"
    shots.mkdir(parents=True)

    def defaults(values):
        return lambda key: values.get(key)

    # Elegida en Cmd+Shift+5 → Opciones: solo `location-last` (caso real en macOS reciente).
    assert screenshot_folders(defaults({"location-last": "~/Desktop/Screenshots"})) == [shots]
    # Las dos, distintas: se vigilan ambas; repetidas, una vez.
    both = {"location-last": str(shots), "location": str(desktop)}
    assert screenshot_folders(defaults(both)) == [shots, desktop]
    same = {"location-last": str(shots), "location": str(shots) + "/"}
    assert screenshot_folders(defaults(same)) == [shots]
    # Nada configurado, o carpetas que ya no existen: el escritorio.
    assert screenshot_folders(defaults({})) == [desktop]
    assert screenshot_folders(defaults({"location": str(tmp_path / "borrada")})) == [desktop]


def test_launch_agent(tmp_path):
    from paste_photo.platforms.macos.autostart import (
        LABEL,
        LaunchAgentAutostart,
        agent_path,
    )

    autostart = LaunchAgentAutostart(tmp_path)
    assert not autostart.is_enabled()
    autostart.enable('"/Users/yo/.local/pipx/venvs/paste-photo/bin/python" -m paste_photo')
    agent = plistlib.loads((tmp_path / f"{LABEL}.plist").read_bytes())
    assert agent["ProgramArguments"] == [
        "/Users/yo/.local/pipx/venvs/paste-photo/bin/python", "-m", "paste_photo"]
    assert agent["RunAtLoad"] is True and agent["Label"] == LABEL
    assert "/opt/homebrew/bin" in agent["EnvironmentVariables"]["PATH"]
    autostart.disable()
    assert not autostart.is_enabled()
    sep = __import__("os").pathsep
    assert agent_path(sep.join(["/a", "/usr/bin"])).split(sep)[:2] == ["/a", "/usr/bin"]


def test_macos_native_host_manifests(tmp_path, monkeypatch):
    from paste_photo.bridge import install, protocol

    monkeypatch.setattr(install.sys, "platform", "darwin")
    support = tmp_path / "Library" / "Application Support"
    (support / "BraveSoftware" / "Brave-Browser").mkdir(parents=True)
    report = install.install_native_host(Path("/opt/paste-photo-native-host"), home=tmp_path)
    # Chrome, Chromium y Firefox siempre; Brave porque existe.
    assert len(report) == 4
    chrome = json.loads((support / "Google" / "Chrome" / "NativeMessagingHosts"
                         / f"{protocol.HOST_NAME}.json").read_text())
    assert chrome["allowed_origins"] == [protocol.EXTENSION_ORIGIN]
    firefox = json.loads((support / "Mozilla" / "NativeMessagingHosts"
                          / f"{protocol.HOST_NAME}.json").read_text())
    assert firefox["allowed_extensions"] == [protocol.FIREFOX_EXTENSION_ID]


def test_synthetic_window_ids_do_not_collide():
    from paste_photo.platforms.macos.accessibility import synthetic_id

    ids = {synthetic_id(pid, index) for pid in (1, 2, 99999) for index in range(3)}
    assert len(ids) == 9 and all(i > 0xFFFFFFFF for i in ids)  # fuera del rango de CGWindowID


def test_parse_rows():
    from paste_photo.targets._applescript import parse_rows

    out = "1\t2\ttrue\thttps://claude.ai/new\tNuevo chat\tcon tab\nbasura\n"
    assert parse_rows(out, 5) == [["1", "2", "true", "https://claude.ai/new",
                                   "Nuevo chat\tcon tab"]]


def test_macos_targets_only_on_macos():
    from paste_photo.targets import supports

    for kind in ("iterm2", "terminal_app", "macos_terminal", "macos_browser"):
        assert supports(kind, "macos") and not supports(kind, "linux")
    for kind in ("tmux", "kitty", "wezterm", "orca", "browser_extension"):
        assert supports(kind, "macos")
    assert not supports("linux_terminal", "macos") and not supports("konsole", "macos")


def test_orca_on_macos():
    from paste_photo.targets.orca import OrcaTarget, default_app_names

    assert default_app_names("macos") == ("orca",)
    assert OrcaTarget(ctx())._paste_text == "\x16"


# --- terminales --------------------------------------------------------------------------------


def test_iterm2_writes_ctrl_v_into_its_session(procs, monkeypatch):
    from paste_photo.targets import iterm2

    calls = []
    monkeypatch.setattr(iterm2, "osascript", lambda script, *args: calls.append(args) or "ok")
    procs += [
        claude(1, TERM_PROGRAM="iTerm.app", ITERM_SESSION_ID="w0t1p0:6A1B-UUID"),
        claude(2, TERM_PROGRAM="ghostty", ITERM_SESSION_ID="w0t0p0:HEREDADO"),  # otro terminal
        claude(3, TERM_PROGRAM="tmux", TMUX="/s,1,0", TMUX_PANE="%1",
               ITERM_SESSION_ID="w0t2p0:X"),  # tmux dentro de iTerm2: lo atiende tmux
    ]
    target = iterm2.ITerm2Target(ctx())
    handle = target.locate()
    assert [c.extra["proc"].pid for c in handle.extra["candidates"]] == [1]
    target.paste(handle)
    assert calls == [("6A1B-UUID", "\x16")]


def test_terminal_app_selects_tab_pastes_and_restores(procs, monkeypatch):
    from paste_photo.targets import terminal_app

    scripts = []

    def fake_osascript(script, *args):
        scripts.append(args)
        return "41\t1\t3\t41" if len(args) == 1 else ""

    monkeypatch.setattr(terminal_app, "osascript", fake_osascript)
    monkeypatch.setattr(terminal_app, "tty_of", lambda pid: "/dev/ttys004")
    procs += [claude(1, TERM_PROGRAM="Apple_Terminal"), claude(2, TERM_PROGRAM="iTerm.app")]
    context = ctx()
    target = terminal_app.TerminalAppTarget(context, settle_ms=0)
    handle = target.locate()
    assert handle.label == "Terminal ttys004" and len(handle.extra["candidates"]) == 1
    target.paste(handle)
    assert scripts == [("/dev/ttys004",), ("41", "1", "0")]  # pestaña 3 → Ctrl+V → la 1
    assert context.keyboard.sent == ["ctrl+v"]


@pytest.mark.parametrize(("selected", "restore"), [
    ("41\t1\t1\t57", ("41", "0", "57")),  # pestañas nativas: vuelve a la ventana 57
    ("41\t1\t1\t41", None),               # Claude ya estaba delante: nada que restaurar
])
def test_terminal_app_restores_native_tab(procs, monkeypatch, selected, restore):
    """Con pestañas nativas cada pestaña es una ventana de AppleScript con una sola pestaña."""
    from paste_photo.targets import terminal_app

    scripts = []

    def fake_osascript(script, *args):
        scripts.append(args)
        return selected if len(args) == 1 else ""

    monkeypatch.setattr(terminal_app, "osascript", fake_osascript)
    monkeypatch.setattr(terminal_app, "tty_of", lambda pid: "/dev/ttys004")
    procs.append(claude(1, TERM_PROGRAM="Apple_Terminal"))
    target = terminal_app.TerminalAppTarget(ctx(), settle_ms=0)
    target.paste(target.locate())
    assert scripts[1:] == ([restore] if restore else [])


def test_macos_terminal_picks_the_window_titled_by_claude(procs):
    from paste_photo.targets.macos_terminal import MacTerminalTarget

    windows = FakeWindows([
        WindowInfo(10, "~/notas", 100),             # otra ventana del mismo Ghostty
        WindowInfo(11, "✳ mi-proyecto", 100),       # la de Claude
        WindowInfo(20, "✳ otro", 200),              # Terminal.app: tiene destino propio
    ])
    procs += [claude(1, ancestors=(50, 100), TERM_PROGRAM="ghostty"),
              claude(2, ancestors=(60, 200), TERM_PROGRAM="Apple_Terminal")]
    context = ctx(windows)
    target = MacTerminalTarget(context, settle_ms=0)
    handle = target.locate()
    assert handle.window_id == 11 and len(handle.extra["candidates"]) == 1
    target.paste(handle)
    assert windows.activated == [11] and context.keyboard.sent == ["ctrl+v"]


def test_macos_terminal_needs_window_system(procs):
    from paste_photo.targets.macos_terminal import MacTerminalTarget

    procs.append(claude(1))
    assert MacTerminalTarget(ctx(windows=None)).locate() is None


# --- navegadores -------------------------------------------------------------------------------


@pytest.fixture
def browsers(monkeypatch):
    """Safari (pid 1) y Firefox (pid 2) abiertos; AppleScript de Safari simulado."""
    from paste_photo.targets import macos_browser

    calls: list[tuple] = []
    safari_tabs = ("7\t1\tfalse\thttps://claude.ai/chat/abc\tProyecto - Claude\n"
                   "7\t2\ttrue\thttps://news.example\tNoticias\n")

    def fake_osascript(script, *args):
        calls.append(args)
        if not args:
            assert 'application id "com.apple.Safari"' in script
            return safari_tabs
        return "2"  # pestaña que estaba seleccionada

    monkeypatch.setattr(macos_browser, "osascript", fake_osascript)
    monkeypatch.setattr(macos_browser, "processes_named", lambda names: [
        SimpleNamespace(pid=1, info={"name": "Safari"})])
    names = {1: "safari", 2: "firefox", 3: "terminal"}
    monkeypatch.setattr(macos_browser, "process_name", lambda pid: names[pid])
    windows = FakeWindows([
        WindowInfo(70, "Noticias", 1),
        WindowInfo(80, "Nuevo chat - Claude", 2),
        WindowInfo(90, "✳ Claude Code", 3),
    ])
    return macos_browser, windows, calls


def test_macos_browser_finds_background_tab_and_restores_it(browsers):
    macos_browser, windows, calls = browsers
    context = ctx(windows)
    context.recency.touch(70)  # Safari, usado más recientemente que Firefox
    target = macos_browser.MacBrowserTarget(context, settle_ms=0)
    handle = target.locate()
    assert [c.label for c in handle.extra["candidates"]] == ["Proyecto - Claude",
                                                            "Nuevo chat - Claude"]
    assert handle.window_id == 70  # ventana de Safari con el título de su pestaña activa
    target.paste(handle)
    assert calls[1:] == [("7", "1", "front"), ("7", "2", "back")]
    assert context.keyboard.sent == ["cmd+v"] and windows.activated == []


def test_macos_browser_window_fallback(browsers):
    macos_browser, windows, calls = browsers
    context = ctx(windows)
    context.recency.touch(80)  # Firefox, el más reciente
    target = macos_browser.MacBrowserTarget(context, settle_ms=0)
    handle = target.locate()
    assert handle.window_id == 80 and handle.label == "Nuevo chat - Claude"
    target.paste(handle)
    assert windows.activated == [80] and context.keyboard.sent == ["cmd+v"]


def test_macos_browser_scripts_use_literal_bundle_ids():
    from paste_photo.targets.macos_browser import list_script, select_script

    chrome = list_script("com.google.Chrome", "chromium")
    assert 'application id "com.google.Chrome"' in chrome and "active tab index of w" in chrome
    safari = select_script("com.apple.Safari", "safari")
    assert "set current tab of w to tab ti of w" in safari and "{" not in safari
