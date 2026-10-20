# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""`paste-photo doctor`: diagnóstico legible de qué funcionará en este equipo y por qué.

Cada comprobación devuelve una línea con ✔ (bien), ⚠ (funciona a medias) o ✘ (no funciona)
y, si hace falta, cómo arreglarlo.
"""

from __future__ import annotations

import json
import platform
import shutil
import sys
from collections.abc import Callable
from pathlib import Path

from paste_photo import __version__
from paste_photo.config import Config

OK, WARN, FAIL = "✔", "⚠", "✘"


def run(config: Config, factory) -> str:
    lines = [f"PastePhoto {__version__} · Python {platform.python_version()} · {sys.platform}"]
    checks: list[Callable[[], list[str]]] = [
        lambda: _session(factory),
        lambda: _tools(factory),
        _bridge,
        _claude_processes,
        _orca,
        lambda: _probe(config, factory),
        _tray,
    ]
    for check in checks:
        try:
            lines += check()
        except Exception as error:  # el diagnóstico nunca debe romperse
            lines.append(f"{FAIL} {check.__name__ if hasattr(check, '__name__') else ''}: "
                         f"{error}")
    return "\n".join(lines)


def _session(factory) -> list[str]:
    if factory.name == "macos":
        return _macos(factory)
    if factory.name != "linux":
        return [f"{OK} Sistema: {factory.name}"]
    session = factory.session
    lines = [f"{OK} Sesión: {session.describe()}"]
    windows = factory.create_window_system()
    if windows is None:
        hint = {"gnome": "ejecuta `paste-photo setup gnome` y vuelve a iniciar sesión",
                "none": "no hay servidor gráfico accesible"}.get(session.backend, "")
        lines.append(f"{WARN} Control de ventanas: no disponible{' (' + hint + ')' if hint else ''}"
                     ". Siguen funcionando el navegador y tmux/kitty/WezTerm/Konsole.")
    else:
        count = len(windows.list_windows())
        lines.append(f"{OK} Control de ventanas ({session.backend}): {count} ventanas visibles")
    source = type(factory.create_screenshot_source()).__name__
    lines.append(f"{OK} Detección de capturas: {source}")
    return lines


def _macos(factory) -> list[str]:
    from paste_photo.platforms.macos.accessibility import is_trusted
    from paste_photo.platforms.macos.sources import screenshot_folder

    lines = [f"{OK} Sistema: macOS {platform.mac_ver()[0]}"]
    if is_trusted():
        windows = factory.create_window_system()
        count = len(windows.list_windows()) if windows is not None else 0
        lines.append(f"{OK} Permiso de Accesibilidad concedido: {count} ventanas visibles")
    else:
        app = Path(sys.executable).resolve()
        lines.append(f"{FAIL} Falta el permiso de Accesibilidad (enfocar ventanas y pulsar la "
                     "tecla de pegado). Ajustes del Sistema → Privacidad y seguridad → "
                     "Accesibilidad: activa la app desde la que lanzas PastePhoto (Terminal, "
                     f"iTerm2...) y, para el inicio automático, {app}. Siguen funcionando la "
                     "extensión del navegador, iTerm2, tmux, kitty y WezTerm.")
    lines.append(f"{OK} Capturas: portapapeles (Cmd+Ctrl+Shift+4) y archivos nuevos en "
                 f"{screenshot_folder()} (Cmd+Shift+4; llegan cuando desaparece la miniatura)")
    lines.append(f"{WARN} La primera vez que pegue en Terminal, iTerm2, Safari o Chrome sin "
                 "extensión, macOS pedirá permiso de Automatización: acéptalo (Ajustes → "
                 "Privacidad y seguridad → Automatización)")
    return lines


def _tools(factory) -> list[str]:
    if factory.name == "macos":
        found = [t for t in ("tmux", "kitty", "wezterm") if shutil.which(t)]
        return [f"{OK} Terminales con IPC instalados: {', '.join(found)}"] if found else []
    if factory.name != "linux":
        return []
    session = factory.session
    lines = []
    clip = "wl-paste" if session.wayland else "xclip"
    if shutil.which(clip):
        lines.append(f"{OK} {clip} instalado (Claude Code lo usa para leer la imagen)")
    else:
        package = "wl-clipboard" if session.wayland else "xclip"
        lines.append(f"{FAIL} Falta {clip}: sudo apt install {package} (o el gestor de tu distro)")
    found = [t for t in ("tmux", "kitty", "wezterm", "konsole") if shutil.which(t)]
    if found:
        lines.append(f"{OK} Terminales con IPC instalados: {', '.join(found)}")
    return lines


def _bridge() -> list[str]:
    from multiprocessing.connection import Client

    from paste_photo.bridge import protocol

    lines = []
    manifests = _installed_host_manifests()
    if manifests:
        lines.append(f"{OK} Host nativo registrado en: {', '.join(manifests)}")
    else:
        lines.append(f"{WARN} Extensión del navegador sin configurar: paste-photo setup browser")
        return lines
    try:
        conn = Client(protocol.address(), family=protocol.family(), authkey=protocol.authkey())
        conn.send_bytes(protocol.encode({"cmd": "status"}))
        browsers = protocol.decode(conn.recv_bytes()).get("browsers", []) if conn.poll(3) else []
        conn.close()
        if browsers:
            lines.append(f"{OK} Extensión conectada en {len(browsers)} navegador(es)")
        else:
            lines.append(f"{WARN} PastePhoto está abierto pero ninguna extensión conectada: "
                         "cárgala en chrome://extensions o instala el .xpi en Firefox "
                         "(ver `paste-photo setup browser`)")
    except (OSError, EOFError):
        lines.append(f"{WARN} PastePhoto no está abierto (no se puede ver si la extensión "
                     "está conectada)")
    return lines


def _installed_host_manifests() -> list[str]:
    from paste_photo.bridge import install

    if sys.platform == "win32":
        import winreg

        found = []
        for browser, (key, _gecko) in install.windows_host_keys().items():
            try:
                winreg.OpenKey(winreg.HKEY_CURRENT_USER, key).Close()
                found.append(browser)
            except OSError:
                pass
        return found
    return [browser for browser, (manifest, _gecko)
            in install.posix_host_manifests(Path.home()).items() if manifest.exists()]


def _claude_processes() -> list[str]:
    if sys.platform == "win32":
        return []
    from paste_photo.targets._env_terminal import IPC_ENV_MARKERS
    from paste_photo.targets._processes import claude_processes

    procs = claude_processes()
    if not procs:
        return [f"{WARN} No hay ningún Claude Code en ejecución en terminales"]
    lines = []
    names = ("tmux", "kitty", "WezTerm", "Konsole", "Orca")
    for proc in procs:
        channel = next((name for name, marker in zip(names, IPC_ENV_MARKERS, strict=True)
                        if all(proc.environ.get(v) for v in marker)), None)
        if channel is None and proc.environ.get("KITTY_WINDOW_ID"):
            lines.append(f"{WARN} Claude (pid {proc.pid}) en kitty sin control remoto: añade "
                         "`allow_remote_control socket-only` y `listen_on unix:@kitty` a "
                         "kitty.conf (si no, se usa la ventana y debe ser la pestaña activa)")
            continue
        how = channel or _macos_channel(proc.environ) or "ventana del terminal (pestaña activa)"
        lines.append(f"{OK} Claude Code (pid {proc.pid}) → {how}")
    return lines


def _macos_channel(environ: dict[str, str]) -> str | None:
    if sys.platform != "darwin":
        return None
    return {"iTerm.app": "iTerm2 (AppleScript, sin foco)",
            "Apple_Terminal": "Terminal (AppleScript selecciona la pestaña)"}.get(
        environ.get("TERM_PROGRAM", ""))


def _orca() -> list[str]:
    from paste_photo.targets.orca import known_cli_paths

    cli = shutil.which("orca") or next((str(p) for p in known_cli_paths() if p.is_file()), None)
    if cli is None:
        return []  # Orca no está instalado: nada que comprobar
    try:
        from paste_photo.targets._env_terminal import run

        status = json.loads(run([cli, "status", "--json"]))["result"]["runtime"]["state"]
    except Exception as error:
        return [f"{WARN} Orca: no se pudo consultar su CLI ({cli}): {error}"]
    if status != "ready":
        return [f"{WARN} Orca instalado pero no abierto (sus terminales no reciben capturas)"]
    return [f"{OK} Orca abierto; CLI: {cli}"]


def _probe(config: Config, factory) -> list[str]:
    from paste_photo.app import probe

    candidates = probe(config, factory)
    if not candidates:
        return [f"{WARN} Ahora mismo no pegaría en ningún sitio (¿Claude abierto?)"]
    return [f"{OK} Pegaría en: " + json.dumps([f"{t}: {label}" for t, label in candidates[:3]],
                                               ensure_ascii=False)]


def _tray() -> list[str]:
    try:
        import pystray

        backend = pystray.Icon.__module__.rsplit(".", 1)[-1].lstrip("_")
    except Exception as error:
        return [f"{FAIL} Bandeja no disponible: {error}"]
    if backend == "xorg":
        return [f"{WARN} Bandeja con el backend básico de X11. En GNOME instala la extensión "
                "'AppIndicator' y python3-gi (pipx install --system-site-packages)."]
    return [f"{OK} Bandeja: {backend}"]
