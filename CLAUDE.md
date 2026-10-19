# CLAUDE.md — paste-photo

Pega automáticamente cada captura de pantalla en el Claude que estés usando: Claude Code en
Windows Terminal (también dentro de WSL) o cualquier chat de claude.ai en Chrome/Edge.
Se instala en Windows y corre en la bandeja del sistema. Diseñado para crecer a macOS/Linux
y a otros destinos (app de escritorio, VS Code) **sin tocar el núcleo**.

## ⚠️ Regla obligatoria: CHANGELOG
**Todo cambio** (código, config, docs, dependencias) se acompaña de una entrada en
`CHANGELOG.md` bajo `## [Unreleased]`, en la categoría de [Keep a Changelog 1.1.0](https://keepachangelog.com/es-ES/1.1.0/):
`Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`.
Una tarea **no está terminada** sin su entrada. Al publicar versión: ver
`packaging/CLAUDE.md` → "Publicar una versión".

## ⚠️ Regla obligatoria: README siempre al día
`README.md` describe **exactamente lo que el producto hace hoy**: funcionalidades
desarrolladas, plataformas soportadas, instalación, uso, configuración y problemas
frecuentes. Cada vez que se añade, cambia o quita una funcionalidad visible para el usuario,
se actualiza el README **en el mismo cambio** (nada de funciones sin documentar ni de
promesas de cosas que aún no existen). Una tarea **no está terminada** sin ello.
El README está en inglés (ver Convenciones).

## Git
- Repositorio privado `igarbayo/paste-photo`; se trabaja directamente sobre `main`.
- Tras **cada** cambio: commit + `git push origin main`.
- Commits **sin firma GPG** (`git -c commit.gpgsign=false commit ...`) y **sin** líneas
  `Co-Authored-By`.
- Mensajes en formato Conventional Commits (`feat:`, `fix:`, `docs:`...).

## Mapa
```
paste_photo/
  core/          dominio puro: eventos, puertos (Protocols), Orchestrator   → core/CLAUDE.md
  platforms/     Abstract Factory por SO (capturas, foco, teclado, autoarranque) → platforms/CLAUDE.md
  targets/       Strategy + Registry: dónde está Claude y cómo pegar         → targets/CLAUDE.md
  ui/            interfaces: bandeja (por defecto) y consola                 → ui/CLAUDE.md
  service.py     PasteService: motor en segundo plano que usan todas las interfaces
  app.py         instancia única, --probe, logs, orden de autoarranque
  config.py      config.toml → Config; guardar ajustes (tomlkit)
  paths.py       rutas de usuario por SO (config y logs)
  resources/     default_config.toml (plantilla y valores por defecto), iconos
  __main__.py    CLI: [tray|run] --probe --list-targets --config --debug
packaging/       build.py, PyInstaller, Inno Setup, winget                  → packaging/CLAUDE.md
.github/workflows/  ci.yml (tests + build) y release.yml (tag vX.Y.Z → release)
tests/           pytest con fakes (tests/fakes.py); corren en cualquier SO
docs/adr/        decisiones de arquitectura
```

Flujo: `ScreenshotSource` (hilo propio) → cola → hilo de trabajo de `PasteService` →
`Orchestrator.handle()` → `locate()` de todos los destinos → se ordenan por la ventana usada
más recientemente (`Recency`) → `paste()` dentro de `preserve_focus()`; si falla, el
siguiente → evento `Pasted`/`NotPasted` a las interfaces suscritas.
Una sola instancia a la vez (bloqueo en `%TEMP%/paste-photo.lock`).

⚠️ Al probar en real: **para siempre** las instancias que lances en segundo plano
(`Get-Process paste-photo*` y `Get-CimInstance Win32_Process ... *paste_photo*`). Una
instancia olvidada con una config de prueba siguió pegando en Chrome en lugar de en la
terminal del usuario.

## Reglas de oro
1. `core/` **nunca** importa nada de un SO ni de `platforms/`/`targets/`/`ui/`.
2. Las librerías de SO se importan **de forma perezosa** (dentro de la factoría o del
   constructor del destino) para que el paquete se importe en cualquier plataforma.
3. Lo nuevo entra por extensión, no por modificación: un SO nuevo = una factoría;
   un destino nuevo = un módulo con `@register_target`; una interfaz nueva = un módulo en
   `ui/` que use `PasteService`; una opción de menú = un `MenuItem` + un método.
4. Las interfaces nunca tocan adaptadores del SO: usan `PasteService` (`submit`, eventos).
5. Todo lo ajustable por el usuario va a `resources/default_config.toml` (comentado).
6. Nunca enviar Enter tras pegar: el usuario decide cuándo enviar.

## Comandos
```bash
python -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev,build]"   # Windows
.venv/Scripts/python -m pytest -q          # tests
.venv/Scripts/ruff check .                 # lint (ruff check --fix . para autoarreglar)
.venv/Scripts/python -m paste_photo                # bandeja
.venv/Scripts/python -m paste_photo run --debug    # consola con logs detallados
.venv/Scripts/python -m paste_photo --probe        # ¿dónde pegaría? (no pega)
.venv/Scripts/python packaging/build.py            # .exe en dist/paste-photo
```
Logs: `%LOCALAPPDATA%\paste-photo\logs\paste-photo.log`. Config del usuario:
`%APPDATA%\paste-photo\config.toml` (se crea desde la plantilla la primera vez).

## Convenciones
- Python ≥ 3.11, type hints en todo, `from __future__ import annotations`.
- Interfaces con `typing.Protocol` (no ABCs); dataclasses `frozen` para valores.
- `logging` (nunca `print`, salvo salida de CLI como `--probe`).
- Código, comentarios, mensajes y docs internas en **español**; `README.md` y `CONTRIBUTING.md` en **inglés** (cara pública del repo).
- Línea máx. 100; ruff con reglas `E,F,I,UP,B`.
- Tests del núcleo con fakes; nada de tests que dependan de ventanas reales.

## Verificación manual (Windows)
1. `--probe` debe listar la pestaña de Claude Code.
2. Arrancar la bandeja, ir a otra app, Win+Shift+S → en el prompt de Claude aparece
   `[Image #N]` sin enviarse y el foco vuelve a la app original.
3. Copiar texto no debe hacer nada; sin Claude abierto, notificación "no hay ningún Claude".
4. Comprobar en pantalla: el contenido de una pestaña de WT se lee por UI Automation
   (control `TermControl`, `TextPattern`); el menú de la bandeja, abriendo el desbordamiento.
⚠️ Si lo ejecutas desde una sesión de Claude Code, la imagen se pegará en **esa** sesión.

## No tocar sin motivo
- `platforms/windows/focus.py`: `AttachThreadInput` + tecla virtual sin asignar (0xE8) para
  poder hacer `SetForegroundWindow`. **Nunca** usar Alt: abre menús en navegadores.
- `paste_keys = "alt+v"`: en Windows Terminal, Ctrl+V solo pega texto.
