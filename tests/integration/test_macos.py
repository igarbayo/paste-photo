# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Integración real en macOS (runner de GitHub): portapapeles, carpeta de capturas, tmux con un
Claude falso y AppleScripts compilados contra las apps reales.

Solo con PASTE_PHOTO_INTEGRATION=1 (CI lo activa). No necesita el permiso de Accesibilidad:
lo que lo requiere (foco, teclas) no se puede conceder en CI y queda para pruebas a mano.
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
    sys.platform != "darwin" or os.environ.get("PASTE_PHOTO_INTEGRATION") != "1",
    reason="integración macOS (PASTE_PHOTO_INTEGRATION=1)",
)

RECEIVER = r'''
import os, sys, tty
log = open(sys.argv[1], "a", buffering=1)
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


def png_bytes(color: str) -> bytes:
    import io

    from PIL import Image

    out = io.BytesIO()
    Image.new("RGB", (32, 32), color).save(out, format="PNG")
    return out.getvalue()


def copy_to_pasteboard(png: bytes) -> None:
    from AppKit import NSData, NSPasteboard

    pasteboard = NSPasteboard.generalPasteboard()
    pasteboard.clearContents()
    pasteboard.setData_forType_(NSData.dataWithBytes_length_(png, len(png)), "public.png")


def pasteboard_png() -> bytes | None:
    from AppKit import NSPasteboard

    data = NSPasteboard.generalPasteboard().dataForType_("public.png")
    return bytes(data) if data is not None else None


def test_clipboard_and_folder_screenshots(tmp_path):
    from paste_photo.platforms.macos.sources import MacScreenshotSource

    events = []
    source = MacScreenshotSource(folder=tmp_path, prefixes=("Screenshot",))
    source.start(events.append)
    try:
        red = png_bytes("red")
        copy_to_pasteboard(red)  # como Cmd+Ctrl+Shift+4
        assert wait_for(lambda: len(events) == 1)
        assert events[0].png() == red

        blue = png_bytes("blue")
        (tmp_path / "notas.png").write_bytes(png_bytes("green"))  # no es una captura
        (tmp_path / "Screenshot 2026-10-20 at 10.15.02.png").write_bytes(blue)  # Cmd+Shift+4
        assert wait_for(lambda: len(events) == 2)
        assert events[1].png() == blue
        assert pasteboard_png() == blue  # copiada para que Claude Code la lea con Ctrl+V
        time.sleep(1)
        assert len(events) == 2  # nuestra copia al portapapeles no cuenta como otra captura
    finally:
        source.stop()


def test_tmux_pane_receives_ctrl_v(tmp_path):
    """Captura real (portapapeles) → PasteService con la familia de macOS → tmux → Claude."""
    if shutil.which("tmux") is None:
        pytest.skip("tmux no instalado (brew install tmux)")
    from paste_photo.config import load_config
    from paste_photo.platforms.macos import MacOSFactory
    from paste_photo.service import PasteService

    # "Claude falso": la línea de órdenes lleva la ruta de Claude Code instalado con npm.
    receiver = tmp_path / "node_modules" / "@anthropic-ai" / "claude-code" / "cli.py"
    receiver.parent.mkdir(parents=True)
    receiver.write_text(RECEIVER, encoding="utf-8")
    log = tmp_path / "tmux.log"
    socket = tmp_path / "tmux.sock"
    os.environ["PASTE_PHOTO_STATE_DIR"] = str(tmp_path / "state")
    os.environ["PASTE_PHOTO_BRIDGE_ADDRESS"] = str(tmp_path / "bridge.sock")
    config = load_config("macos", Path(__file__).resolve().parents[2]
                         / "paste_photo" / "resources" / "default_config.toml")
    service = PasteService(config, MacOSFactory())
    events = []
    service.subscribe(events.append)
    subprocess.run(["tmux", "-S", str(socket), "new-session", "-d",
                    f"'{sys.executable}' '{receiver}' '{log}'"], check=True)
    try:
        service.start()
        assert wait_for(lambda: log.exists() and "READY" in log.read_text())
        copy_to_pasteboard(png_bytes("purple"))
        assert wait_for(lambda: "16" in log.read_text().split()), log.read_text()
        assert wait_for(lambda: any(getattr(e, "target", None) == "tmux" for e in events))
    finally:
        service.stop()
        subprocess.run(["tmux", "-S", str(socket), "kill-server"])
        from paste_photo.bridge.server import BridgeServer

        if BridgeServer._instance is not None:
            BridgeServer._instance.stop()
            BridgeServer._instance = None


def _compile(script: str, tmp_path: Path) -> None:
    source = tmp_path / "script.applescript"
    source.write_text(script, encoding="utf-8")
    result = subprocess.run(["osacompile", "-o", str(tmp_path / "script.scpt"), str(source)],
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr


APP_FOLDERS = ("/Applications", "/System/Applications", "/System/Applications/Utilities",
               "/System/Volumes/Preboot/Cryptexes/App/System/Applications")  # Safari


def _installed(app: str) -> bool:
    return any(Path(base, f"{app}.app").exists() for base in APP_FOLDERS)


@pytest.mark.parametrize(("app", "script"), [
    ("Terminal", "terminal_app.SELECT_SCRIPT"),
    ("Terminal", "terminal_app.RESTORE_SCRIPT"),
    ("iTerm", "iterm2.WRITE_SCRIPT"),
    ("Safari", "safari.list"),
    ("Safari", "safari.select"),
    ("Google Chrome", "chromium.list"),
    ("Google Chrome", "chromium.select"),
])
def test_applescripts_compile(app, script, tmp_path):
    """Errores de sintaxis o de vocabulario de cada app (sin ejecutar nada)."""
    if not _installed(app):
        pytest.skip(f"{app} no está instalado")
    from paste_photo.targets import iterm2, macos_browser, terminal_app

    modules = {"terminal_app": terminal_app, "iterm2": iterm2}
    kind, name = script.split(".")
    if kind in modules:
        text = getattr(modules[kind], name)
    else:
        bundle = {"safari": "com.apple.Safari", "chromium": "com.google.Chrome"}[kind]
        builder = macos_browser.list_script if name == "list" else macos_browser.select_script
        text = builder(bundle, kind)
    _compile(text, tmp_path)
