# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Fuentes de capturas en Linux.

| Sesión              | Fuente                                                      |
|---------------------|-------------------------------------------------------------|
| X11 / XWayland      | `X11ClipboardSource`: evento XFixes al cambiar el portapapeles |
| KDE, wlroots        | `WlPasteWatchSource`: `wl-paste --watch` (protocolo data-control) |
| GNOME Wayland       | `ScreenshotFolderSource`: GNOME no deja vigilar el portapapeles; |
|                     | se vigila la carpeta donde guarda las capturas (que también copia) |
"""

from __future__ import annotations

import hashlib
import logging
import shutil
import subprocess
import threading
import time
from collections.abc import Callable, Iterable
from pathlib import Path

from paste_photo.core.events import ScreenshotCaptured
from paste_photo.imaging import cached, to_png

log = logging.getLogger(__name__)

OnCapture = Callable[[ScreenshotCaptured], None]
IMAGE_TYPES = ("image/png", "image/jpeg", "image/bmp", "image/webp")
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".bmp")


def make_event(data: bytes) -> ScreenshotCaptured:
    return ScreenshotCaptured(image_hash=hashlib.sha1(data).hexdigest(),
                              timestamp=time.monotonic(), load_png=cached(lambda: to_png(data)))


def _run(cmd: list[str], timeout: float = 5) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(cmd, capture_output=True, timeout=timeout)


def pick_image_type(types: Iterable[str]) -> str | None:
    available = {t.strip() for t in types}
    return next((t for t in IMAGE_TYPES if t in available), None)


# --- X11 -------------------------------------------------------------------------------


class X11ClipboardSource:
    """XFixes avisa cada vez que alguien toma el portapapeles; la imagen se lee con xclip."""

    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._on_capture: OnCapture | None = None

    def start(self, on_capture: OnCapture) -> None:
        if shutil.which("xclip") is None:
            raise RuntimeError("Falta xclip (sudo apt install xclip)")
        self._on_capture = on_capture
        self._thread = threading.Thread(target=self._loop, name="x11-clipboard", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        try:
            self._watch()
        except Exception:
            log.exception("Se detuvo la vigilancia del portapapeles X11")

    def _watch(self) -> None:
        from Xlib import display
        from Xlib.ext import xfixes

        d = display.Display()
        d.xfixes_query_version()
        root = d.screen().root
        clipboard = d.intern_atom("CLIPBOARD")
        # Método del display añadido por la extensión (no aparece en dir()).
        d.xfixes_select_selection_input(root, clipboard,
                                        xfixes.XFixesSetSelectionOwnerNotifyMask)
        d.flush()
        while not self._stop.is_set():
            if not d.pending_events():
                time.sleep(0.1)  # sondeo barato para poder parar el hilo
                continue
            event = d.next_event()
            if getattr(event, "selection", None) != clipboard:
                continue
            time.sleep(0.05)  # dejar que el dueño nuevo termine de prepararse
            self._read()

    def _read(self) -> None:
        try:
            types = _run(["xclip", "-selection", "clipboard", "-t", "TARGETS", "-o"])
            mime = pick_image_type(types.stdout.decode(errors="replace").splitlines())
            if mime is None:
                return
            data = _run(["xclip", "-selection", "clipboard", "-t", mime, "-o"]).stdout
        except (OSError, subprocess.SubprocessError) as error:
            log.warning("No se pudo leer el portapapeles: %s", error)
            return
        if data and self._on_capture:
            self._on_capture(make_event(data))


# --- Wayland con data-control (KDE, wlroots) -----------------------------------------------


class WlPasteWatchSource:
    """`wl-paste --watch` imprime una línea en cada cambio del portapapeles."""

    def __init__(self) -> None:
        self._proc: subprocess.Popen[bytes] | None = None
        self._on_capture: OnCapture | None = None

    @staticmethod
    def supported() -> bool:
        if shutil.which("wl-paste") is None:
            return False
        # GNOME no implementa data-control: wl-paste --watch sale con error enseguida.
        try:
            probe = subprocess.Popen(["wl-paste", "--watch", "true"], stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
            time.sleep(0.5)
            alive = probe.poll() is None
            probe.terminate()
            return alive
        except OSError:
            return False

    def start(self, on_capture: OnCapture) -> None:
        self._on_capture = on_capture
        self._proc = subprocess.Popen(["wl-paste", "--watch", "echo", "changed"],
                                      stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        threading.Thread(target=self._loop, name="wl-paste-watch", daemon=True).start()

    def stop(self) -> None:
        if self._proc is not None:
            self._proc.terminate()

    def _loop(self) -> None:
        assert self._proc is not None and self._proc.stdout is not None
        for _line in self._proc.stdout:
            try:
                types = _run(["wl-paste", "--list-types"]).stdout.decode(errors="replace")
                mime = pick_image_type(types.splitlines())
                if mime is None:
                    continue
                data = _run(["wl-paste", "--no-newline", "--type", mime]).stdout
            except (OSError, subprocess.SubprocessError) as error:
                log.warning("No se pudo leer el portapapeles: %s", error)
                continue
            if data and self._on_capture:
                self._on_capture(make_event(data))


# --- Carpeta de capturas (GNOME Wayland y como complemento) ----------------------------------


def default_screenshot_dirs() -> list[Path]:
    """Carpetas habituales: GNOME y Spectacle guardan en Imágenes/Screenshots."""
    pictures = None
    if shutil.which("xdg-user-dir"):
        try:
            out = _run(["xdg-user-dir", "PICTURES"]).stdout.decode().strip()
            pictures = Path(out) if out else None
        except (OSError, subprocess.SubprocessError):
            pictures = None
    pictures = pictures or Path.home() / "Pictures"
    # Solo subcarpetas de capturas: vigilar Imágenes entera pegaría cualquier foto guardada.
    names = ("Screenshots", "Capturas de pantalla", "Capturas", "Bildschirmfotos")
    return [pictures / name for name in names]


class ScreenshotFolderSource:
    """Sondea carpetas buscando imágenes nuevas (sin dependencias; 0,5 s de latencia)."""

    def __init__(self, folders: Iterable[Path] | None = None, interval_s: float = 0.5) -> None:
        self._folders = [Path(f) for f in (folders or default_screenshot_dirs())]
        self._interval = interval_s
        self._stop = threading.Event()
        self._on_capture: OnCapture | None = None
        self._seen: set[Path] = set()

    def start(self, on_capture: OnCapture) -> None:
        self._on_capture = on_capture
        self._seen = set(self._images())  # solo cuenta lo que llegue a partir de ahora
        threading.Thread(target=self._loop, name="screenshot-folder", daemon=True).start()

    def stop(self) -> None:
        self._stop.set()

    def _images(self) -> list[Path]:
        found = []
        for folder in self._folders:
            if folder.is_dir():
                found += [p for p in folder.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES]
        return found

    def _loop(self) -> None:
        while not self._stop.wait(self._interval):
            for path in self._images():
                if path in self._seen:
                    continue
                if self._settled(path):
                    self._seen.add(path)
                    data = path.read_bytes()
                    if data and self._on_capture:
                        self._on_capture(make_event(data))

    @staticmethod
    def _settled(path: Path) -> bool:
        """El archivo terminó de escribirse (tamaño estable)."""
        try:
            size = path.stat().st_size
            time.sleep(0.15)
            return size > 0 and path.stat().st_size == size
        except OSError:
            return False


# --- Combinación -------------------------------------------------------------------------


class CompositeSource:
    """Varias fuentes a la vez. Si dos avisan de la misma captura casi a la vez (portapapeles
    y archivo), solo cuenta la primera."""

    def __init__(self, sources: list, window_s: float = 1.5) -> None:
        self._sources = sources
        self._window = window_s
        self._last = 0.0
        self._lock = threading.Lock()

    def start(self, on_capture: OnCapture) -> None:
        def forward(source_index: int) -> OnCapture:
            def handler(event: ScreenshotCaptured) -> None:
                with self._lock:
                    duplicate = (time.monotonic() - self._last < self._window
                                 and self._last_source != source_index)
                    if not duplicate:  # solo las capturas aceptadas abren la ventana
                        self._last, self._last_source = time.monotonic(), source_index
                if not duplicate:
                    on_capture(event)
            return handler

        self._last_source = -1
        for index, source in enumerate(self._sources):
            source.start(forward(index))

    def stop(self) -> None:
        for source in self._sources:
            source.stop()
