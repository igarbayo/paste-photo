# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Capturas en macOS: portapapeles y carpeta de capturas, en un mismo hilo.

- Cmd+Ctrl+Shift+3/4 (o "Copiar al portapapeles" en Cmd+Shift+5) dejan la imagen en el
  portapapeles: se sondea `NSPasteboard.changeCount` (no hay aviso de cambios).
- Cmd+Shift+3/4/5 por defecto **solo guardan un archivo** (escritorio o la carpeta elegida).
  Claude Code lee la imagen del portapapeles al pulsar Ctrl+V, así que la captura se copia al
  portapapeles (como hace GNOME) y ese cambio propio no se vuelve a contar.

La carpeta elegida en Cmd+Shift+5 → Opciones se guarda en `location-last` (macOS reciente;
p. ej. `~/Desktop/Screenshots`) y la fijada con `defaults write ... location`, en `location`:
se vigilan las dos (y el escritorio si no hay ninguna), y se vuelven a leer cada pocos
segundos por si el usuario cambia de carpeta con PastePhoto abierto.
"""

from __future__ import annotations

import hashlib
import logging
import subprocess
import threading
import time
from collections.abc import Callable, Iterable
from pathlib import Path

from paste_photo.core.events import ScreenshotCaptured
from paste_photo.imaging import cached, to_png

log = logging.getLogger(__name__)

OnCapture = Callable[[ScreenshotCaptured], None]

# Tipos de imagen del portapapeles, por preferencia. Las capturas traen PNG; "Copiar imagen"
# de muchas apps, TIFF.
IMAGE_TYPES = ("public.png", "public.tiff")
# Si hay archivos copiados (Finder), la imagen es solo su icono: no es una captura.
FILE_TYPES = ("public.file-url", "NSFilenamesPboardType")
# Nombre de los archivos de captura según el idioma del sistema (o el que el usuario fije con
# `defaults write com.apple.screencapture name`).
SCREENSHOT_PREFIXES = (
    "Screenshot", "Screen Shot", "Captura de pantalla", "Bildschirmfoto", "Capture d’écran",
    "Capture d'écran", "Istantanea schermo", "Schermafbeelding", "Captura de Tela",
    "Captura de ecrã", "Skärmavbild", "Skjermbilde", "Skærmbillede", "Näyttökuva",
    "Zrzut ekranu", "Snímek obrazovky", "Снимок экрана", "スクリーンショット", "스크린샷",
    "截屏", "螢幕截圖", "Ekran Resmi",
)
SCREENSHOT_SUFFIXES = (".png", ".jpg", ".jpeg", ".tiff")
# Claves de `com.apple.screencapture` con la carpeta de las capturas, por prioridad.
LOCATION_KEYS = ("location-last", "location")
FOLDERS_REFRESH_S = 5.0


def make_event(data: bytes) -> ScreenshotCaptured:
    return ScreenshotCaptured(image_hash=hashlib.sha1(data).hexdigest(),
                              timestamp=time.monotonic(), load_png=cached(lambda: to_png(data)))


def pick_pasteboard_type(types: Iterable[str]) -> str | None:
    available = set(types)
    if available & set(FILE_TYPES):
        return None
    return next((t for t in IMAGE_TYPES if t in available), None)


def _defaults_read(key: str) -> str | None:
    try:
        result = subprocess.run(["defaults", "read", "com.apple.screencapture", key],
                                capture_output=True, text=True, timeout=3)
    except (OSError, subprocess.SubprocessError):
        return None
    value = result.stdout.strip()
    return value if result.returncode == 0 and value else None


def screenshot_folders(read: Callable[[str], str | None] = _defaults_read) -> list[Path]:
    """Donde macOS guarda las capturas: `location-last` y `location` (las que existan, sin
    repetir); si no hay ninguna, el escritorio."""
    folders: list[Path] = []
    for key in LOCATION_KEYS:
        value = read(key)
        if not value:
            continue
        folder = Path(value).expanduser()
        if folder.is_dir() and folder.resolve() not in {f.resolve() for f in folders}:
            folders.append(folder)
    return folders or [Path.home() / "Desktop"]


def screenshot_prefixes() -> tuple[str, ...]:
    custom = _defaults_read("name")
    return ((custom,) if custom else ()) + SCREENSHOT_PREFIXES


def is_screenshot_file(path: Path, prefixes: Iterable[str]) -> bool:
    # macOS escribe primero un archivo oculto (".Captura...") y luego lo renombra.
    name = path.name
    return (not name.startswith(".") and path.suffix.lower() in SCREENSHOT_SUFFIXES
            and any(name.startswith(prefix) for prefix in prefixes))


class MacScreenshotSource:
    def __init__(self, folders: Iterable[Path] | None = None,
                 prefixes: Iterable[str] | None = None, interval_s: float = 0.25,
                 watch_folder: bool = True) -> None:
        # Carpetas fijas (pruebas); si no, las de la configuración de macOS, releídas.
        self._fixed_folders = list(folders) if folders is not None else None
        self._folders: list[Path] = []
        self._folders_checked = 0.0
        self._prefixes = tuple(prefixes) if prefixes is not None else None
        self._interval = interval_s
        self._watch_folder = watch_folder
        self._stop = threading.Event()
        self._on_capture: OnCapture | None = None
        self._seen: set[Path] = set()
        self._last_count = -1
        self._own_count = -1  # cambio del portapapeles hecho por nosotros

    def start(self, on_capture: OnCapture) -> None:
        from AppKit import NSPasteboard

        self._on_capture = on_capture
        self._pasteboard = NSPasteboard.generalPasteboard()
        self._last_count = self._pasteboard.changeCount()  # lo que ya había no cuenta
        if self._watch_folder:
            self._prefixes = self._prefixes or screenshot_prefixes()
            self._refresh_folders()
        threading.Thread(target=self._loop, name="mac-screenshots", daemon=True).start()

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        import objc

        while not self._stop.wait(self._interval):
            try:
                with objc.autorelease_pool():
                    self._check_pasteboard()
                    if self._watch_folder:
                        self._check_folder()
            except Exception:
                log.exception("Error vigilando las capturas")

    # --- portapapeles ----------------------------------------------------------------

    def _check_pasteboard(self) -> None:
        count = self._pasteboard.changeCount()
        if count == self._last_count:
            return
        self._last_count = count
        if count == self._own_count:
            return
        mime = pick_pasteboard_type(str(t) for t in (self._pasteboard.types() or []))
        if mime is None:
            return
        data = self._pasteboard.dataForType_(mime)
        if data is not None and data.length() and self._on_capture:
            self._on_capture(make_event(bytes(data)))

    # --- carpeta de capturas ---------------------------------------------------------

    def _refresh_folders(self) -> None:
        self._folders_checked = time.monotonic()
        folders = self._fixed_folders if self._fixed_folders is not None \
            else screenshot_folders()
        new = [f for f in folders if f not in self._folders]
        for folder in new:  # lo que ya hubiera en una carpeta nueva no cuenta
            self._seen |= set(self._screenshots(folder))
        if new or len(folders) != len(self._folders):
            log.debug("Vigilando capturas en %s", ", ".join(map(str, folders)))
        self._folders = list(folders)

    def _screenshots(self, folder: Path) -> list[Path]:
        assert self._prefixes is not None
        try:
            return [p for p in folder.iterdir() if is_screenshot_file(p, self._prefixes)]
        except OSError:
            return []

    def _check_folder(self) -> None:
        if time.monotonic() - self._folders_checked > FOLDERS_REFRESH_S:
            self._refresh_folders()
        for path in [p for folder in self._folders for p in self._screenshots(folder)]:
            if path in self._seen or not _settled(path):
                continue
            self._seen.add(path)
            event = make_event(path.read_bytes())
            png = event.png()
            if png:
                self._copy_to_pasteboard(png)
                if self._on_capture:
                    self._on_capture(event)

    def _copy_to_pasteboard(self, png: bytes) -> None:
        from AppKit import NSData

        self._pasteboard.clearContents()
        self._pasteboard.setData_forType_(NSData.dataWithBytes_length_(png, len(png)),
                                          "public.png")
        self._own_count = self._last_count = self._pasteboard.changeCount()


def _settled(path: Path) -> bool:
    """El archivo terminó de escribirse (tamaño estable)."""
    try:
        size = path.stat().st_size
        time.sleep(0.15)
        return size > 0 and path.stat().st_size == size
    except OSError:
        return False
