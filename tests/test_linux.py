# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Lógica de Linux que no necesita un escritorio: detección de sesión, teclas, parseos,
elección de destino por entorno del proceso, fuentes de capturas, autostart y manifiestos."""

import json
import time

import pytest

from paste_photo.core.ports import TargetHandle, WindowInfo
from paste_photo.platforms.linux import session as session_mod
from paste_photo.targets import _processes
from paste_photo.targets._processes import ClaudeProcess
from paste_photo.targets.registry import TargetContext
from tests.fakes import FakeFocus, FakeKeyboard

# --- sesión --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("env", "wayland", "desktop", "backend"),
    [
        ({"XDG_SESSION_TYPE": "x11", "DISPLAY": ":0", "XDG_CURRENT_DESKTOP": "XFCE"},
         False, "other", "x11"),
        ({"XDG_SESSION_TYPE": "wayland", "XDG_CURRENT_DESKTOP": "ubuntu:GNOME",
          "WAYLAND_DISPLAY": "wayland-0", "DISPLAY": ":0"}, True, "gnome", "gnome"),
        ({"XDG_SESSION_TYPE": "wayland", "XDG_CURRENT_DESKTOP": "KDE",
          "WAYLAND_DISPLAY": "wayland-0"}, True, "kde", "kde"),
        ({"WAYLAND_DISPLAY": "wayland-0", "DISPLAY": ":0"}, True, "other", "x11"),  # WSLg
        ({"XDG_SESSION_TYPE": "wayland", "XDG_CURRENT_DESKTOP": "sway",
          "WAYLAND_DISPLAY": "wayland-1"}, True, "other", "none"),
        ({"XDG_SESSION_TYPE": "wayland", "PASTE_PHOTO_BACKEND": "x11"}, True, "other", "x11"),
    ],
)
def test_session_detection(env, wayland, desktop, backend):
    s = session_mod.detect(env)
    assert (s.wayland, s.desktop, s.backend) == (wayland, desktop, backend)


# --- teclas y parseos (sin X ni D-Bus) ------------------------------------------------------


def test_x11_keysyms():
    from paste_photo.platforms.linux.x11 import keysym_names

    assert keysym_names("ctrl+v") == (["Control_L"], "v")
    assert keysym_names("ctrl+shift+v") == (["Control_L", "Shift_L"], "v")


def test_portal_key_sequence():
    from paste_photo.platforms.linux.kde import key_sequence

    assert key_sequence("ctrl+v") == [(0xFFE3, 1), (ord("v"), 1), (ord("v"), 0), (0xFFE3, 0)]


def test_kwin_report_parsing():
    from paste_photo.platforms.linux.kde import parse_report, window_number

    payload = json.dumps([
        {"id": "{aaaa}", "title": "✳ proyecto", "pid": 42, "app_id": "org.kde.konsole",
         "active": True},
        {"id": "{bbbb}", "title": "Firefox", "pid": 7, "app_id": "firefox", "active": False},
    ])
    windows, uuids, active = parse_report(payload)
    assert [w.title for w in windows] == ["✳ proyecto", "Firefox"]
    assert active == window_number("{aaaa}") and uuids[active] == "{aaaa}"


def test_gnome_windows_parsing():
    from paste_photo.platforms.linux.gnome import parse_windows

    windows = parse_windows('[{"id": 3, "title": "✳ x", "pid": 9, "app_id": "Ptyxis"}]')
    assert windows == [WindowInfo(3, "✳ x", 9, "Ptyxis")]


# --- destinos según el entorno del proceso claude --------------------------------------------


def ctx(windows=None) -> TargetContext:
    return TargetContext(platform="linux", focus=FakeFocus(), keyboard=FakeKeyboard(),
                         windows=windows)


def claude(pid, ancestors=(100,), **env) -> ClaudeProcess:
    return ClaudeProcess(pid, dict(env), tuple(ancestors))


@pytest.fixture
def procs(monkeypatch):
    found: list[ClaudeProcess] = []
    for module in ("paste_photo.targets._env_terminal", "paste_photo.targets.linux_terminal"):
        monkeypatch.setattr(f"{module}.claude_processes", lambda: list(found))
    return found


def test_tmux_wins_over_outer_kitty(procs):
    from paste_photo.targets.kitty import KittyTarget
    from paste_photo.targets.tmux import TmuxTarget, tmux_socket

    procs.append(claude(1, TMUX="/tmp/tmux-1000/default,55,0", TMUX_PANE="%3",
                        KITTY_WINDOW_ID="2", KITTY_LISTEN_ON="unix:@kitty"))
    assert TmuxTarget(ctx()).locate().label == "tmux %3"
    assert KittyTarget(ctx()).locate() is None  # Ctrl+V por kitty iría al panel activo de tmux
    assert tmux_socket("/tmp/tmux-1000/default,55,0") == "/tmp/tmux-1000/default"


def test_kitty_needs_remote_control(procs):
    from paste_photo.targets.kitty import KittyTarget

    procs.append(claude(1, KITTY_WINDOW_ID="2"))  # sin KITTY_LISTEN_ON
    assert KittyTarget(ctx()).locate() is None


def test_env_target_sends_and_falls_back(procs, monkeypatch):
    from paste_photo.targets.wezterm import WezTermTarget

    procs += [claude(1, WEZTERM_PANE="0"), claude(2, WEZTERM_PANE="1")]
    sent = []

    def fake_send(self, proc):
        sent.append(proc.environ["WEZTERM_PANE"])
        if proc.environ["WEZTERM_PANE"] == "0":
            raise RuntimeError("pane cerrado")

    monkeypatch.setattr(WezTermTarget, "send_ctrl_v", fake_send)
    target = WezTermTarget(ctx())
    target.paste(target.locate())
    assert sent == ["0", "1"]


class FakeWindows:
    def __init__(self, windows):
        self.windows, self.activated = windows, []

    def list_windows(self):
        return self.windows

    def active_window(self):
        return None

    def activate(self, window_id):
        self.activated.append(window_id)


def test_linux_terminal_uses_window_of_active_claude_tab(procs):
    from paste_photo.targets.linux_terminal import LinuxTerminalTarget

    windows = FakeWindows([WindowInfo(10, "✳ mi-proyecto", 100), WindowInfo(20, "bash", 200)])
    procs += [claude(1, ancestors=(50, 100)), claude(2, ancestors=(60, 200)),
              claude(3, ancestors=(70,), TMUX="/s,1,0", TMUX_PANE="%1")]  # este es de tmux
    context = ctx(windows)
    target = LinuxTerminalTarget(context, settle_ms=0)
    handle = target.locate()
    assert handle.window_id == 10 and len(handle.extra["candidates"]) == 1  # el 2: otra pestaña
    target.paste(handle)
    assert windows.activated == [10] and context.keyboard.sent == ["ctrl+v"]


def test_linux_terminal_needs_window_system(procs):
    from paste_photo.targets.linux_terminal import LinuxTerminalTarget

    procs.append(claude(1))
    assert LinuxTerminalTarget(ctx(windows=None)).locate() is None


def test_linux_browser_pastes_into_window_whose_active_tab_is_claude(monkeypatch):
    from paste_photo.targets import linux_browser

    names = {1: "firefox-esr", 2: "epiphany", 3: "firefox-esr", 4: "xterm"}
    monkeypatch.setattr(linux_browser, "process_name", lambda pid: names[pid])
    windows = FakeWindows([
        WindowInfo(10, "Nuevo chat - Claude — Mozilla Firefox", 1),
        WindowInfo(20, "Proyecto - Claude", 2),               # GNOME Web: sin sufijo
        WindowInfo(30, "Noticias — Mozilla Firefox", 3),        # otra pestaña activa
        WindowInfo(40, "✳ Claude Code", 4),                     # terminal: no es navegador
    ])
    context = ctx(windows)
    context.recency.touch(20)
    target = linux_browser.LinuxBrowserTarget(context, settle_ms=0)
    handle = target.locate()
    assert handle.window_id == 20  # el usado más recientemente
    target.paste(handle)
    assert windows.activated == [20] and context.keyboard.sent == ["ctrl+v"]


def test_linux_browser_needs_window_system():
    from paste_photo.targets.linux_browser import LinuxBrowserTarget

    assert LinuxBrowserTarget(ctx(windows=None)).locate() is None


def test_owning_window_walks_ancestors():
    windows = [WindowInfo(1, "a", 300), WindowInfo(2, "b", 200)]
    assert _processes.owning_window((100, 200, 300), windows).id == 2
    assert _processes.owning_window((5,), windows) is None


# --- prioridad con last_used (extensión) ---------------------------------------------------


def test_orchestrator_uses_target_last_used():
    from paste_photo.core.orchestrator import Orchestrator
    from paste_photo.core.recency import Recency

    recency = Recency()
    recency.touch(10, at=time.time() - 60)  # terminal usada hace un minuto
    orch = Orchestrator([], FakeFocus(), recency=recency)
    browser = TargetHandle(0, "chat", {"last_used": time.time()})
    terminal = TargetHandle(10, "term")
    assert orch.last_used(browser) > orch.last_used(terminal)


# --- fuentes de capturas -----------------------------------------------------------------------


def test_pick_image_type():
    from paste_photo.platforms.linux.sources import pick_image_type

    assert pick_image_type(["TARGETS", "image/bmp", "image/png"]) == "image/png"
    assert pick_image_type(["UTF8_STRING", "text/plain"]) is None


def test_folder_source_reports_only_new_files(tmp_path):
    from paste_photo.platforms.linux.sources import ScreenshotFolderSource

    (tmp_path / "old.png").write_bytes(b"\x89PNG old")
    events = []
    source = ScreenshotFolderSource([tmp_path], interval_s=0.05)
    source.start(events.append)
    try:
        (tmp_path / "Screenshot 1.png").write_bytes(b"\x89PNG\r\n\x1a\n new")
        (tmp_path / "notes.txt").write_text("no")
        deadline = time.time() + 5
        while not events and time.time() < deadline:
            time.sleep(0.05)
    finally:
        source.stop()
    assert len(events) == 1 and events[0].png().startswith(b"\x89PNG\r\n\x1a\n")


def test_composite_source_drops_same_capture_from_second_source():
    from paste_photo.platforms.linux.sources import CompositeSource, make_event

    class Manual:
        def start(self, on_capture):
            self.emit = on_capture

        def stop(self):
            pass

    a, b, got = Manual(), Manual(), []
    composite = CompositeSource([a, b], window_s=1.0)
    composite.start(got.append)
    a.emit(make_event(b"one"))
    b.emit(make_event(b"one-as-file"))  # misma captura vista por la otra fuente
    a.emit(make_event(b"two"))  # misma fuente: es otra captura
    assert len(got) == 2


# --- autostart y manifiestos -------------------------------------------------------------------


def test_xdg_autostart(tmp_path):
    from paste_photo.platforms.linux.desktop import XdgAutostart

    autostart = XdgAutostart(tmp_path)
    assert not autostart.is_enabled()
    autostart.enable("/usr/bin/paste-photo")
    text = (tmp_path / "paste-photo.desktop").read_text()
    assert "Exec=/usr/bin/paste-photo" in text and autostart.is_enabled()
    autostart.disable()
    assert not autostart.is_enabled()


def test_linux_native_host_manifests(tmp_path, monkeypatch):
    from pathlib import Path

    from paste_photo.bridge import install, protocol

    monkeypatch.setattr(install.sys, "platform", "linux")
    (tmp_path / ".config" / "BraveSoftware" / "Brave-Browser").mkdir(parents=True)
    (tmp_path / ".librewolf").mkdir()
    report = install.install_native_host(Path("/usr/bin/paste-photo-native-host"), home=tmp_path)
    # Chrome, Chromium y Firefox siempre; Brave y LibreWolf porque existen.
    assert len(report) == 5
    manifest = json.loads((tmp_path / ".config" / "chromium" / "NativeMessagingHosts"
                           / f"{protocol.HOST_NAME}.json").read_text())
    assert manifest["allowed_origins"] == [f"chrome-extension://{protocol.EXTENSION_ID}/"]
    assert manifest["path"] == str(Path("/usr/bin/paste-photo-native-host"))
    for folder in (".mozilla", ".librewolf"):
        gecko = json.loads((tmp_path / folder / "native-messaging-hosts"
                            / f"{protocol.HOST_NAME}.json").read_text())
        assert gecko["allowed_extensions"] == [protocol.FIREFOX_EXTENSION_ID]
        assert "allowed_origins" not in gecko


def test_firefox_extension_from_chromium(tmp_path):
    import zipfile

    from paste_photo.bridge import install, protocol

    xpi = install.build_firefox_extension(tmp_path / "extension-firefox")
    with zipfile.ZipFile(xpi) as archive:
        names = set(archive.namelist())
        manifest = json.loads(archive.read("manifest.json"))
    assert {"manifest.json", "background.js", "cursor.js"} <= names
    assert "key" not in manifest
    assert manifest["background"] == {"scripts": ["background.js"]}
    assert manifest["browser_specific_settings"]["gecko"]["id"] == protocol.FIREFOX_EXTENSION_ID
    assert manifest["content_scripts"][0]["js"] == ["cursor.js"]


def test_extension_id_matches_manifest_key():
    import base64
    import hashlib
    from pathlib import Path

    from paste_photo.bridge.protocol import EXTENSION_ID

    manifest = json.loads((Path(__file__).parent.parent / "paste_photo" / "resources"
                           / "extension" / "manifest.json").read_text(encoding="utf-8"))
    digest = hashlib.sha256(base64.b64decode(manifest["key"])).hexdigest()[:32]
    assert "".join(chr(ord("a") + int(c, 16)) for c in digest) == EXTENSION_ID


def test_is_claude_with_plain_process_objects():
    """Los padres de un proceso no traen `info` (solo los de process_iter)."""
    import os

    import psutil

    assert _processes.is_claude(psutil.Process(os.getpid())) is False


class _FakeProc:
    def __init__(self, name, cmdline):
        self.info = {"name": name, "cmdline": cmdline}


@pytest.mark.parametrize(("name", "cmdline", "expected"), [
    ("claude", ["claude"], True),
    ("node", ["node", "/usr/lib/node_modules/@anthropic-ai/claude-code/cli.js"], True),
    # instalador nativo: el proceso se llama como la versión (enlace a versions/2.1.304)
    ("2.1.304", ["claude"], True),
    ("2.1.304", ["/Users/yo/.local/bin/claude", "--continue"], True),
    # la app de escritorio de macOS no es Claude Code
    ("Claude", ["/Applications/Claude.app/Contents/MacOS/Claude"], False),
    # otro bundle (el Python de python.org se relanza desde Python.app) sí puede ser Claude Code
    ("Python", ["/Library/Frameworks/Python.framework/Versions/3.12/Resources/Python.app/"
                "Contents/MacOS/Python", "/x/node_modules/@anthropic-ai/claude-code/cli.py"],
     True),
    ("python3", ["python3", "claude.py"], False),
    # el puente de Claude in Chrome que lanza el navegador
    ("2.1.304", ["/Users/yo/.local/bin/claude", "--chrome-native-host"], False),
])
def test_is_claude_by_name_argv0_and_npm_path(name, cmdline, expected):
    assert _processes.is_claude(_FakeProc(name, cmdline)) is expected
