# Changelog

Todos los cambios relevantes de este proyecto se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/)
y el proyecto se adhiere a [Semantic Versioning](https://semver.org/lang/es/).

## [Unreleased]

## [0.2.1] - 2026-10-19

### Added
- Licencia **MIT** (`LICENSE`, `LICENSES/MIT.txt`) y cabeceras SPDX en todo el código Python.
- `docs/COMPONENTS_LICENSE.md`: análisis de licencias de todos los componentes
  (dependencias, binarios nativos del instalador, herramientas, recursos y marcas).
- El instalador incluye `LICENSE`, `THIRD-PARTY-NOTICES.txt` y los textos completos de las
  licencias de terceros (`licenses/`), generados por `packaging/third_party.py`, y muestra
  la licencia durante la instalación.
- Secciones de licencia en README y CONTRIBUTING, y regla de licencias en `CLAUDE.md`.

### Changed
- pystray (LGPL-3.0) se distribuye como código fuente sustituible en `_internal/pystray/`
  para cumplir la LGPL; `build.py` falla si no es así.
- Manifiestos de winget con `License: MIT`, `LicenseUrl` y `Copyright`.
- `pyproject.toml` declara `license = "MIT"` (requiere setuptools ≥ 77).

## [0.2.0] - 2026-10-19

### Added
- **Icono en la bandeja del sistema** (modo por defecto): activar/pausar, elegir dónde pegar,
  notificaciones, "¿Dónde pegaría ahora?", abrir configuración y registro, iniciar con
  Windows y salir. Los ajustes del menú se guardan en `config.toml` sin perder comentarios.
- **Instalador de Windows** (Inno Setup, por usuario, sin permisos de administrador): menú
  Inicio, inicio automático y PATH opcionales, desinstalador que limpia ambos.
- Dos ejecutables (PyInstaller): `paste-photo.exe` (bandeja, sin consola) y
  `paste-photo-cli.exe` (`run`, `--probe`... desde una terminal).
- **GitHub Actions**: CI (lint y tests en Windows y Linux, build del `.exe`) y release al
  subir un tag `vX.Y.Z` (instalador, SHA-256 y manifiestos de winget en la release).
- **winget**: generación y validación de manifiestos (`igarbayo.paste-photo`) y envío
  automático opcional a microsoft/winget-pkgs.
- `PasteService`: servicio en segundo plano reutilizable por cualquier interfaz (eventos
  `Pasted`, `NotPasted`, `StateChanged`; órdenes en el hilo de trabajo).
- Modo consola explícito: `paste-photo run`.
- Registro en archivo rotativo (`%LOCALAPPDATA%\paste-photo\logs`).
- La primera ejecución crea `%APPDATA%\paste-photo\config.toml` desde la plantilla.
- Si se abre una segunda instancia sin consola, avisa con una ventana.
- Icono de la aplicación (`packaging/make_icon.py`).
- Regla en `CLAUDE.md`: el README debe reflejar siempre las funcionalidades desarrolladas.
- README actualizado: instalación (instalador, winget, código fuente), bandeja, CLI,
  configuración, desinstalación y problemas frecuentes.
- `ui/CLAUDE.md` y `packaging/CLAUDE.md` con recetas para ampliar la bandeja y publicar.
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
- `paste-photo` sin argumentos abre la bandeja; el modo consola anterior es `paste-photo run`.
- La configuración por defecto vive en el paquete (`paste_photo/resources/default_config.toml`).
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

[Unreleased]: https://github.com/igarbayo/paste-photo/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/igarbayo/paste-photo/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/igarbayo/paste-photo/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/igarbayo/paste-photo/releases/tag/v0.1.0
