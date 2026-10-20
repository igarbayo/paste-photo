# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""CLI.

    paste-photo                  icono en la bandeja (modo por defecto)
    paste-photo run              modo consola, con logs en pantalla (Ctrl+C para salir)
    paste-photo doctor           diagnóstico: qué funcionará en este equipo y cómo arreglarlo
    paste-photo setup browser    registra la extensión del navegador (Chrome, Edge, Brave...)
    paste-photo setup gnome      instala la extensión de GNOME Shell (GNOME Wayland)
    paste-photo --probe          dónde pegaría ahora, sin pegar nada
    paste-photo --list-targets   tipos de destino disponibles

En el instalador de Windows, `paste-photo.exe` no tiene consola (bandeja) y
`paste-photo-cli.exe` sí (para `run`, `--probe`... desde una terminal).
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from paste_photo import __version__
from paste_photo.paths import user_log_file

MODES = ("tray", "run", "doctor", "setup")
SETUP_WHAT = ("browser", "gnome")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="paste-photo", description="Pega automáticamente tus capturas en Claude."
    )
    parser.add_argument("mode", nargs="?", choices=MODES, default="tray",
                        help="tray (por defecto), run (consola), doctor, setup")
    parser.add_argument("what", nargs="?", choices=SETUP_WHAT,
                        help="para setup: browser o gnome")
    parser.add_argument("--config", type=Path, help="ruta a config.toml")
    parser.add_argument("--debug", action="store_true", help="logs detallados")
    parser.add_argument("--probe", action="store_true", help="muestra dónde pegaría y sale")
    parser.add_argument("--list-targets", action="store_true", help="lista los tipos de destino")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    # Los títulos de Claude llevan glifos (✳ ◑) que la consola cp1252 no imprime.
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    if args.mode == "setup" and args.what is None:
        parser.error("indica qué configurar: paste-photo setup browser | gnome")
    interactive = args.mode in ("run", "doctor", "setup") or args.probe or args.list_targets
    from paste_photo.app import setup_logging

    setup_logging(user_log_file(), console=interactive, debug=args.debug)
    log = logging.getLogger("paste_photo")

    try:
        return _dispatch(args)
    except Exception:
        log.exception("Error inesperado")
        return 1


def _dispatch(args: argparse.Namespace) -> int:
    from paste_photo.app import AlreadyRunningError, launch_command, probe, single_instance
    from paste_photo.config import ensure_user_config, load_config
    from paste_photo.platforms.factory import get_platform_factory
    from paste_photo.targets import available_targets

    log = logging.getLogger("paste_photo")
    if args.list_targets:
        print("\n".join(available_targets()))
        return 0
    if args.mode == "setup":
        return _setup(args.what)

    factory = get_platform_factory()
    if args.config is None:
        ensure_user_config()  # la primera vez crea %APPDATA%\paste-photo\config.toml
    config = load_config(factory.name, args.config)
    log.debug("Config: %s", config.source or "valores por defecto")

    if args.mode == "doctor":
        from paste_photo import doctor

        print(doctor.run(config, factory))
        return 0

    if args.probe:
        candidates = probe(config, factory)
        if not candidates:
            print("No hay ninguna sesión de Claude abierta")
            return 1
        for position, (target, label) in enumerate(candidates, start=1):
            print(f"{position}. {target:<18} -> {label!r}")
        return 0

    from paste_photo.service import PasteService

    service = PasteService(config, factory)
    try:
        with single_instance():
            if args.mode == "run":
                from paste_photo.ui.console import run_console

                run_console(service)
            else:
                _run_tray(service, config, factory, launch_command())
    except AlreadyRunningError as error:
        log.error("%s", error)
        _tell_user_already_running(str(error), interactive=args.mode == "run")
        return 2
    return 0


def _setup(what: str) -> int:
    if what == "browser":
        from paste_photo.bridge.install import setup_browser

        print(setup_browser())
        return 0
    if sys.platform != "linux":
        print("La extensión de GNOME Shell solo existe en Linux.")
        return 1
    from paste_photo.platforms.linux.gnome import install_extension

    print(install_extension())
    return 0


def _run_tray(service, config, factory, command: str) -> None:
    from paste_photo.config import ensure_user_config
    from paste_photo.ui.tray import TrayApp

    try:
        autostart = factory.create_autostart()
    except NotImplementedError:
        autostart = None
    TrayApp(
        service,
        config,
        config_path=config.source or ensure_user_config(),
        log_path=user_log_file(),
        autostart=autostart,
        launch_command=command,
        autostart_label="Iniciar con Windows" if sys.platform == "win32"
        else "Iniciar al iniciar sesión",
    ).run()


def _tell_user_already_running(message: str, *, interactive: bool) -> None:
    """Sin consola (doble clic en el .exe) el usuario no vería el error: ventana nativa."""
    if interactive or sys.platform != "win32" or sys.stderr is not None:
        return
    import ctypes

    ctypes.windll.user32.MessageBoxW(None, message, "PastePhoto", 0x40)  # MB_ICONINFORMATION


if __name__ == "__main__":
    sys.exit(main())
