# Changelog

Todos los cambios relevantes de este proyecto se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/)
y el proyecto se adhiere a [Semantic Versioning](https://semver.org/lang/es/).

## [Unreleased]

## [0.1.0] - 2026-10-19

### Added
- Detección de capturas en Windows escuchando cambios de imagen en el portapapeles
  (`AddClipboardFormatListener`), compatible con Win+Shift+S.
- Destino `windows_terminal`: localiza la pestaña de Claude Code por UI Automation y
  `title_regex`, pega con Alt+V y restaura la pestaña y la ventana anteriores.
- Núcleo independiente del SO: puertos (`ScreenshotSource`, `FocusManager`, `Keyboard`,
  `TargetStrategy`) y `Orchestrator` con cadena de destinos y deduplicación.
- Factoría por plataforma con stubs para macOS y Linux.
- Registro de destinos con stubs para `desktop_app`, `browser` y `vscode`.
- Configuración `config.toml` y CLI con `--probe`, `--list-targets`, `--debug` y `--config`.
- Documentación: README, CLAUDE.md (raíz, `core/`, `platforms/`, `targets/`), ADR 0001.

[Unreleased]: https://github.com/igarbayo/paste-photo/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/igarbayo/paste-photo/releases/tag/v0.1.0
