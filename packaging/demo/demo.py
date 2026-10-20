# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Graba la demo del README (docs/assets/demo.gif) con PastePhoto y Claude Code reales.

    .venv/Scripts/python packaging/demo/demo.py           # Windows, pantalla principal

Qué hace (unos 30 s; no toques el ratón ni el teclado mientras graba):
1. Abre la escena: fondo liso, una app de facturas con un fallo y Windows Terminal con
   Claude Code en ~/invoice-app (carpeta temporal), sin las variables de esta sesión.
2. Arranca PastePhoto limitado a esa terminal (título "PastePhoto demo"): no puede pegar en
   ninguna otra sesión de Claude.
3. Escribe una pregunta en Claude Code (sin enviarla), hace la captura de verdad con
   Win+Shift+S y deja que PastePhoto la pegue.
4. Monta el GIF con rótulos y lo cierra todo (la sesión de Claude Code se cierra sin enviar).

La captura de pantalla de Windows no incluye el puntero ni el rectángulo de Recortes: se
dibujan en el GIF a partir de la posición real del ratón.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ctypes.windll.shcore.SetProcessDpiAwareness(2)

import win32api  # noqa: E402
import win32con  # noqa: E402
import win32gui  # noqa: E402
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageGrab, ImageStat  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))
from paste_photo.platforms.windows.focus import WindowsFocusManager  # noqa: E402

OUT = REPO / "docs" / "assets" / "demo.gif"
PROJECT = Path.home() / "invoice-app"
DEMO_TITLE = "PastePhoto demo"
APP_RECT = (60, 180, 880, 740)       # app de facturas (x0, y0, x1, y1), píxeles físicos
TERM_RECT = (920, 120, 1880, 840)    # Windows Terminal con Claude Code
REGION = (30, 90, 1910, 870)         # zona grabada
FPS = 10
QUESTION = "Why is the total NaN? "
GIF_WIDTH, BAR = 960, 76
BRAND, DARK = (217, 119, 87), (31, 29, 26)
CAPTIONS = {  # rótulo interno → (paso, texto)
    "": (None, "PastePhoto"),
    "ask": ("1", "You're asking Claude Code about a bug"),
    "snip": ("2", "Take a screenshot as usual (Win + Shift + S)"),
    "paste": ("3", "PastePhoto pastes it at your cursor. Nothing is sent."),
}
INVOICE_PY = '''"""Tiny invoice calculator (demo project)."""

ITEMS = [("Design", 1200), ("Hosting", 240), ("Support", None)]


def total(items):
    return sum(price for _, price in items)
'''

# --- teclado y ratón -----------------------------------------------------------------------

KEYEVENTF_KEYUP, KEYEVENTF_UNICODE = 0x2, 0x4


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wt.WORD), ("wScan", wt.WORD), ("dwFlags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class _INPUT(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [("ki", _KEYBDINPUT), ("pad", ctypes.c_byte * 32)]
    _anonymous_ = ("u",)
    _fields_ = [("type", wt.DWORD), ("u", _U)]


def key(vk: int = 0, scan: int = 0, flags: int = 0) -> None:
    inp = _INPUT(type=1)
    inp.ki = _KEYBDINPUT(vk, scan, flags, 0, 0)
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))


def type_text(text: str, delay: float = 0.07) -> None:
    for ch in text:
        key(scan=ord(ch), flags=KEYEVENTF_UNICODE)
        key(scan=ord(ch), flags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP)
        time.sleep(delay)


def move(x: int, y: int, steps: int = 1, duration: float = 0.0) -> None:
    sx, sy = win32api.GetCursorPos()
    for i in range(1, steps + 1):
        win32api.SetCursorPos((int(sx + (x - sx) * i / steps), int(sy + (y - sy) * i / steps)))
        time.sleep(duration / steps)


def snip_hotkey() -> None:
    for vk in (0x5B, 0x10, 0x53):  # Win, Shift, S
        key(vk=vk)
    for vk in (0x53, 0x10, 0x5B):
        key(vk=vk, flags=KEYEVENTF_KEYUP)


# --- ventanas ------------------------------------------------------------------------------

def find(title: str) -> int | None:
    found: list[int] = []
    win32gui.EnumWindows(lambda h, _: found.append(h) if win32gui.IsWindowVisible(h)
                         and win32gui.GetWindowText(h) == title else None, None)
    return found[0] if found else None


def wait_for(title: str, timeout: float = 30) -> int:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if hwnd := find(title):
            return hwnd
        time.sleep(0.5)
    raise RuntimeError(f"no aparece la ventana {title!r}")


def place(hwnd: int, rect: tuple[int, int, int, int]) -> None:
    x0, y0, x1, y1 = rect
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.MoveWindow(hwnd, x0, y0, x1 - x0, y1 - y0, True)


def close(title: str) -> None:
    while hwnd := find(title):
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        time.sleep(1)


def open_scene() -> tuple[int, int]:
    PROJECT.mkdir(exist_ok=True)
    (PROJECT / "invoice.py").write_text(INVOICE_PY, encoding="utf-8")
    subprocess.Popen([sys.executable, str(HERE / "scene_windows.py"), "backdrop"])
    subprocess.Popen([sys.executable, str(HERE / "scene_windows.py"), "app"])
    # Sin las variables de la sesión de Claude que lanza esto (avisos en la cabecera).
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("CLAUDE")}
    subprocess.Popen(["wt.exe", "-w", "new", "--title", DEMO_TITLE, "--suppressApplicationTitle",
                      "-d", str(PROJECT), "powershell", "-NoLogo", "-NoExit", "-Command",
                      "claude --permission-mode default"], env=env)
    app, term = wait_for("Invoices"), wait_for(DEMO_TITLE)
    time.sleep(10)  # que arranque Claude Code
    focus = WindowsFocusManager()
    for hwnd, rect in ((app, APP_RECT), (term, TERM_RECT)):
        place(hwnd, rect)
        focus.activate(hwnd)
        time.sleep(0.3)
    return app, term


def close_scene() -> None:
    for title in (DEMO_TITLE, "Invoices", "PastePhoto backdrop"):
        close(title)
    shutil.rmtree(PROJECT, ignore_errors=True)


# --- grabación -----------------------------------------------------------------------------

class Recorder(threading.Thread):
    def __init__(self) -> None:
        super().__init__(daemon=True)
        self.frames: list = []
        self.running, self.caption = True, ""

    def run(self) -> None:
        x0, y0 = REGION[:2]
        while self.running:
            t = time.monotonic()
            img = ImageGrab.grab(bbox=REGION)
            cx, cy = win32api.GetCursorPos()
            self.frames.append((t, img, (cx - x0, cy - y0), self.caption))
            time.sleep(max(0.0, 1 / FPS - (time.monotonic() - t)))


def record(app: int, term: int, log_file: Path) -> tuple[list, tuple[int, int]]:
    cfg = log_file.with_name("cfg.toml")
    cfg.write_text('[general]\nnotify = false\n\n[[targets]]\ntype = "windows_terminal"\n'
                   f'title_regex = "^{DEMO_TITLE}$"\n', encoding="utf-8")
    with log_file.open("w", encoding="utf-8") as log:
        paste_photo = subprocess.Popen([sys.executable, "-m", "paste_photo", "run", "--debug",
                                        "--config", str(cfg)], cwd=REPO, stdout=log,
                                       stderr=subprocess.STDOUT)
    focus, rec = WindowsFocusManager(), Recorder()
    x0, y0, x1, y1 = APP_RECT
    drag_start = (x0 + 30, y0 + 70)
    try:
        time.sleep(4)
        focus.activate(term)
        move(1300, 640)
        rec.start()
        time.sleep(1.2)
        rec.caption = "ask"
        type_text(QUESTION)
        time.sleep(1.0)
        rec.caption = "snip"
        move(470, 450, steps=12, duration=0.6)
        focus.activate(app)
        time.sleep(0.6)
        snip_hotkey()
        time.sleep(1.6)  # superposición de Recortes
        move(*drag_start, steps=10, duration=0.5)
        time.sleep(0.3)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
        move(x1 - 40, y1 - 60, steps=25, duration=1.2)
        time.sleep(0.2)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)
        rec.caption = "paste"
        end = time.monotonic() + 10
        while time.monotonic() < end and "Pegando imagen" not in log_file.read_text("utf-8"):
            time.sleep(0.2)
        time.sleep(4.5)
    finally:
        rec.running = False
        rec.join(3)
        paste_photo.terminate()
        paste_photo.wait(10)
    if "Pegando imagen" not in log_file.read_text("utf-8"):
        raise RuntimeError(f"PastePhoto no pegó la captura (ver {log_file})")
    return rec.frames, (drag_start[0] - REGION[0], drag_start[1] - REGION[1])


# --- GIF -----------------------------------------------------------------------------------

def _brightness(img: Image.Image) -> float:
    return sum(ImageStat.Stat(img.convert("L").resize((64, 32))).mean)


def _arrow(d: ImageDraw.ImageDraw, x: float, y: float) -> None:
    pts = [(0, 0), (0, 17), (4, 13), (7, 20), (10, 19), (7, 12), (12, 12)]
    d.polygon([(x + px, y + py) for px, py in pts], fill="white", outline="black")


def _crosshair(d: ImageDraw.ImageDraw, x: float, y: float) -> None:
    for width, color in ((3, "white"), (1, "black")):
        for dx, dy in ((-10, 0), (10, 0), (0, -10), (0, 10)):
            d.line((x, y, x + dx, y + dy), fill=color, width=width)


def _caption_bar(step: str | None, text: str) -> Image.Image:
    bar = Image.new("RGB", (GIF_WIDTH, BAR), DARK)
    d = ImageDraw.Draw(bar)
    x = 28
    if step:
        r = 20
        d.ellipse((x, BAR // 2 - r, x + 2 * r, BAR // 2 + r), fill=BRAND)
        d.text((x + r, BAR // 2), step, font=ImageFont.load_default(22), fill="white",
               anchor="mm")
        x += 2 * r + 18
    d.text((x, BAR // 2), text, font=ImageFont.load_default(25), fill="white", anchor="lm")
    return bar


def build_gif(frames: list, drag_start: tuple[int, int]) -> None:
    scale = GIF_WIDTH / frames[0][1].width
    normal = _brightness(frames[0][1])
    out: list[Image.Image] = []
    durations: list[int] = []
    last_bright, pressed = frames[0][1], False
    for i, (t, img, (cx, cy), caption) in enumerate(frames):
        img = img.convert("RGB")
        dim = _brightness(img) < normal * 0.8  # superposición de Recortes
        if not dim:
            last_bright, pressed = img, False
        else:
            # El rectángulo de Recortes no sale en la captura: se redibuja desde el punto
            # donde se pulsó hasta el puntero, con la imagen sin oscurecer.
            if abs(cx - drag_start[0]) < 6 and abs(cy - drag_start[1]) < 6:
                pressed = True
            if pressed and cx > drag_start[0] + 4:
                box = (*drag_start, cx, cy)
                img = img.copy()
                img.paste(last_bright.crop(box), box[:2])
                ImageDraw.Draw(img).rectangle(box, outline=(255, 255, 255), width=3)
        frame = img.resize((GIF_WIDTH, int(img.height * scale)), Image.LANCZOS)
        d = ImageDraw.Draw(frame)
        x, y = cx * scale, cy * scale
        if 0 <= x < frame.width and 0 <= y < frame.height:
            (_crosshair if dim else _arrow)(d, x, y)
        canvas = Image.new("RGB", (GIF_WIDTH, frame.height + BAR))
        canvas.paste(frame, (0, 0))
        canvas.paste(_caption_bar(*CAPTIONS[caption]), (0, frame.height))
        duration = int(((frames[i + 1][0] if i + 1 < len(frames) else t + 0.1) - t) * 1000)
        if out and not ImageChops.difference(out[-1], canvas).getbbox():
            durations[-1] += duration  # fotograma repetido: se alarga el anterior
        else:
            out.append(canvas)
            durations.append(duration)
    durations[0] += 600
    durations[-1] += 2500  # pausa antes de repetir
    out[0].save(OUT, save_all=True, append_images=out[1:], duration=durations, loop=0,
                optimize=True, disposal=1)
    print(f"{OUT}: {len(out)} fotogramas, {OUT.stat().st_size // 1024} KB, "
          f"{sum(durations) / 1000:.1f} s")


def main() -> int:
    if sys.platform != "win32":
        raise SystemExit("La demo se graba en Windows (Windows Terminal + Recortes).")
    if PROJECT.exists():
        raise SystemExit(f"{PROJECT} ya existe: la demo la crea y la borra; muévela antes.")
    work = Path(tempfile.mkdtemp(prefix="pastephoto-demo-"))
    try:
        app, term = open_scene()
        frames, drag_start = record(app, term, work / "run.log")
        build_gif(frames, drag_start)
    finally:
        close_scene()
        shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
