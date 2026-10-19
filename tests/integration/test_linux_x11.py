# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Integración real en Linux/X11: Xvfb + Openbox + terminales reales + un Claude falso.

Solo se ejecuta con PASTE_PHOTO_INTEGRATION=1 (CI lo activa). Necesita: Xvfb, openbox,
xterm, tmux, xclip y xdpyinfo (x11-utils). Cada prueba hace una captura de verdad (imagen
en el portapapeles X11) y comprueba que el Claude falso recibe Ctrl+V (byte 0x16).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "linux" or os.environ.get("PASTE_PHOTO_INTEGRATION") != "1",
    reason="integración Linux/X11 (PASTE_PHOTO_INTEGRATION=1)",
)

RECEIVER = r'''
import os, sys, termios, tty
log = open(sys.argv[1], "a", buffering=1)
sys.stdout.write("\033]0;✳ sesion-prueba\007"); sys.stdout.flush()
fd = sys.stdin.fileno(); tty.setraw(fd); log.write("READY\n")
while True:
    data = os.read(fd, 64)
    if not data:
        break
    log.write(data.hex() + "\n")
'''


def wait_for(predicate, timeout=10.0, step=0.1):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(step)
    return False


@pytest.fixture(scope="module")
def x11(tmp_path_factory):
    display = ":97"
    xvfb = subprocess.Popen(["Xvfb", display, "-screen", "0", "1280x800x24"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    env = {**os.environ, "DISPLAY": display, "XDG_SESSION_TYPE": "x11"}
    env.pop("WAYLAND_DISPLAY", None)
    assert wait_for(lambda: subprocess.run(["xdpyinfo"], env=env, capture_output=True)
                    .returncode == 0)
    wm = subprocess.Popen(["openbox"], env=env, stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL)
    time.sleep(1)
    old = {k: os.environ.get(k) for k in ("DISPLAY", "XDG_SESSION_TYPE", "WAYLAND_DISPLAY")}
    os.environ.update({"DISPLAY": display, "XDG_SESSION_TYPE": "x11"})
    os.environ.pop("WAYLAND_DISPLAY", None)
    base = tmp_path_factory.mktemp("fake-claude")
    claude = base / "claude"  # el proceso se llamará "claude", como Claude Code
    shutil.copy(os.path.realpath(sys.executable), claude)
    (base / "recv.py").write_text(RECEIVER, encoding="utf-8")
    yield {"env": env, "claude": claude, "recv": base / "recv.py", "base": base}
    for key, value in old.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    wm.terminate()
    xvfb.terminate()


@pytest.fixture
def service(x11, tmp_path):
    from paste_photo.config import load_config
    from paste_photo.platforms.linux import LinuxFactory
    from paste_photo.service import PasteService

    config = load_config("linux", Path(__file__).resolve().parents[2]
                         / "paste_photo" / "resources" / "default_config.toml")
    os.environ["PASTE_PHOTO_STATE_DIR"] = str(tmp_path / "state")
    os.environ["PASTE_PHOTO_BRIDGE_ADDRESS"] = str(tmp_path / "bridge.sock")
    svc = PasteService(config, LinuxFactory())
    events = []
    svc.subscribe(events.append)
    svc.start()
    yield svc, events
    svc.stop()
    from paste_photo.bridge.server import BridgeServer

    if BridgeServer._instance is not None:
        BridgeServer._instance.stop()
        BridgeServer._instance = None


def capture(x11, color):
    from PIL import Image

    png = x11["base"] / f"shot-{color}.png"
    Image.new("RGB", (32, 32), color).save(png)
    subprocess.run(["xclip", "-selection", "clipboard", "-t", "image/png", "-i", str(png)],
                   env=x11["env"], check=True)


def received_ctrl_v(log: Path) -> bool:
    return log.exists() and "16" in log.read_text().split()


def test_tmux_pane_receives_ctrl_v(x11, service, tmp_path):
    log = tmp_path / "tmux.log"
    socket = tmp_path / "tmux.sock"
    subprocess.run(["tmux", "-S", str(socket), "new-session", "-d",
                    f"{x11['claude']} {x11['recv']} {log}"], env=x11["env"], check=True)
    try:
        assert wait_for(lambda: log.exists() and "READY" in log.read_text())
        capture(x11, "red")
        assert wait_for(lambda: received_ctrl_v(log)), log.read_text()
        assert wait_for(lambda: any(getattr(e, "target", None) == "tmux" for e in service[1]))
    finally:
        subprocess.run(["tmux", "-S", str(socket), "kill-server"], env=x11["env"])


def test_any_terminal_gets_focus_and_ctrl_v(x11, service, tmp_path):
    from paste_photo.platforms.linux.x11 import X11WindowSystem

    log = tmp_path / "xterm.log"
    other = subprocess.Popen(["xterm", "-T", "otra-ventana", "-e", "sleep", "60"], env=x11["env"])
    term = subprocess.Popen(["xterm", "-T", "arrancando", "-e", str(x11["claude"]),
                             str(x11["recv"]), str(log)], env=x11["env"])
    try:
        assert wait_for(lambda: log.exists() and "READY" in log.read_text())
        windows = X11WindowSystem()
        other_id = next(w.id for w in windows.list_windows() if w.title == "otra-ventana")
        windows.activate(other_id)
        assert wait_for(lambda: windows.active_window() == other_id)
        capture(x11, "green")
        assert wait_for(lambda: received_ctrl_v(log)), log.read_text()
        assert wait_for(lambda: any(getattr(e, "target", None) == "linux_terminal"
                                    for e in service[1]))
        # El foco vuelve a la ventana en la que estaba el usuario.
        assert wait_for(lambda: windows.active_window() == other_id)
    finally:
        other.terminate()
        term.terminate()
