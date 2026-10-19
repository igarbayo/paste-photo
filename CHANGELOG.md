# Changelog

Todos los cambios relevantes de este proyecto se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/)
y el proyecto se adhiere a [Semantic Versioning](https://semver.org/lang/es/).

## [Unreleased]

### Added
- Prioridad por uso reciente (`general.prefer = "recent"`, por defecto): con Claude abierto
  en varios sitios, la captura va al que usaste por última vez (p. ej. la terminal en la que
  estás escribiendo, aunque también haya un chat en el navegador). `prefer = "order"`
  mantiene el comportamiento anterior.
- `--probe` muestra el orden completo en que se intentaría pegar.
- Soporte de Claude Code dentro de WSL en Windows Terminal (`wsl = true`): se comprueba
  dentro de la distro que hay un `claude` en marcha.
- Una sola instancia de paste-photo a la vez (bloqueo en el directorio temporal).
- Tabla de teclas de pegado de imágenes por sistema operativo en `targets/CLAUDE.md`.
- `CONTRIBUTING.md` (en inglés): entorno, flujo de pull requests, estilo, Conventional
  Commits y definición de terminado.
- Destino `browser`: pega en cualquier chat de Claude en la web (claude.ai: Chat, Code,
  Design...) en Chrome, Edge y demás navegadores Chromium. Detecta por URL la pestaña
  visible y por título las de segundo plano, y solo pega si la pestaña tiene el prompt.
- Si una pestaña candidata no tiene prompt (falso positivo), se prueba la siguiente.
- Base `UiaTabTarget` (Template Method) compartida por los destinos con pestañas de Windows.
- Dependencia `psutil`.

### Changed
- `browser` forma parte de los destinos por defecto en Windows, detrás de `windows_terminal`.
- Si un destino falla al pegar, se prueba el siguiente en vez de perder la captura.
- `README.md` reescrito en inglés y simplificado; el detalle de opciones queda en `config.toml`.

### Removed
- `general.debounce_ms`: sustituido por `general.remember_images`.

### Fixed
- Una misma imagen se volvía a pegar minutos después (al quitarla del chat reaparecía)
  cuando otra app la devolvía al portapapeles: ahora cada imagen se pega una sola vez
  (se recuerdan las últimas `remember_images`, 100 por defecto).
- Una pestaña de Windows Terminal cuyo Claude había terminado seguía siendo destino: ahora
  se exige un proceso `claude` vivo bajo esa ventana (`require_process`, activo por defecto).
- Ya no llegan pulsaciones sueltas de Alt a la ventana destino al cambiar el foco (abrían la
  barra de menús en navegadores): se usa `AttachThreadInput` y, si no basta, una tecla
  virtual sin asignar.
- Errores COM al recorrer el árbol de UI Automation mientras cambia la página.

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
