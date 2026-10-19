"""CLI: `python -m paste_photo [--config RUTA] [--debug] [--probe] [--list-targets]`."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from paste_photo import __version__
from paste_photo.app import probe, run
from paste_photo.config import load_config
from paste_photo.platforms.factory import get_platform_factory
from paste_photo.targets import available_targets


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="paste-photo", description="Pega automáticamente tus capturas en Claude Code."
    )
    parser.add_argument("--config", type=Path, help="ruta a config.toml")
    parser.add_argument("--debug", action="store_true", help="logs detallados")
    parser.add_argument("--probe", action="store_true", help="muestra qué destino se usaría y sale")
    parser.add_argument("--list-targets", action="store_true", help="lista los tipos de destino")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    # Los títulos de Claude Code llevan glifos (✳ ◑) que la consola cp1252 no imprime.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("comtypes").setLevel(logging.WARNING)  # ruido de uiautomation

    if args.list_targets:
        print("\n".join(available_targets()))
        return 0

    factory = get_platform_factory()
    config = load_config(factory.name, args.config)
    logging.getLogger(__name__).debug("Config: %s", config.source or "valores por defecto")

    if args.probe:
        return probe(config, factory)
    run(config, factory)
    return 0


if __name__ == "__main__":
    sys.exit(main())
