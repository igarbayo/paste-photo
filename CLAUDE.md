# CLAUDE.md — paste-photo

Pega automáticamente cada captura de pantalla en la sesión de Claude Code abierta.
MVP: Windows + Windows Terminal. Diseñado para crecer a macOS/Linux y a otros destinos
(app de escritorio, navegador, VS Code) **sin tocar el núcleo**.

## ⚠️ Regla obligatoria: CHANGELOG
**Todo cambio** (código, config, docs, dependencias) se acompaña de una entrada en
`CHANGELOG.md` bajo `## [Unreleased]`, en la categoría de [Keep a Changelog 1.1.0](https://keepachangelog.com/es-ES/1.1.0/):
`Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`.
Una tarea **no está terminada** sin su entrada. Al publicar versión: renombrar
`[Unreleased]` a `[X.Y.Z] - AAAA-MM-DD` (SemVer), crear un `[Unreleased]` vacío,
actualizar los enlaces del pie y `paste_photo/__version__`.

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
  platforms/     Abstract Factory por SO (fuente de capturas, foco, teclado) → platforms/CLAUDE.md
  targets/       Strategy + Registry: dónde está Claude y cómo pegar         → targets/CLAUDE.md
  config.py      config.toml → Config (búsqueda: --config, ./, dir de usuario)
  app.py         composition root: cablea todo, bucle principal, --probe
  __main__.py    CLI
tests/           pytest con fakes (tests/fakes.py); corren en cualquier SO
docs/adr/        decisiones de arquitectura
```

Flujo: `ScreenshotSource` (hilo propio) → `queue` → `Orchestrator.handle()` (hilo
principal) → `locate()` de todos los destinos → se ordenan por la ventana usada más
recientemente (`Recency`) → `paste()` dentro de `preserve_focus()`; si falla, el siguiente.
Una sola instancia a la vez (bloqueo en `%TEMP%/paste-photo.lock`).

⚠️ Al probar en real: **para siempre** las instancias que lances en segundo plano
(`Get-CimInstance Win32_Process ... *paste_photo*`). Una instancia olvidada con una config de
prueba siguió pegando en Chrome en lugar de en la terminal del usuario.

## Reglas de oro
1. `core/` **nunca** importa nada de un SO ni de `platforms/`/`targets/`.
2. Las librerías de SO se importan **de forma perezosa** (dentro de la factoría o del
   constructor del destino) para que el paquete se importe en cualquier plataforma.
3. Lo nuevo entra por extensión, no por modificación: un SO nuevo = una factoría;
   un destino nuevo = un módulo con `@register_target`.
4. Todo lo ajustable por el usuario va a `config.toml` con valor por defecto en código.
5. Nunca enviar Enter tras pegar: el usuario decide cuándo enviar.

## Comandos
```bash
python -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev]"   # Windows
.venv/Scripts/python -m pytest -q          # tests
.venv/Scripts/ruff check .                 # lint (ruff check --fix . para autoarreglar)
.venv/Scripts/python -m paste_photo --probe        # ¿qué pestaña se usaría? (no pega)
.venv/Scripts/python -m paste_photo --list-targets
.venv/Scripts/python -m paste_photo --debug        # ejecutar con logs detallados
```

## Convenciones
- Python ≥ 3.11, type hints en todo, `from __future__ import annotations`.
- Interfaces con `typing.Protocol` (no ABCs); dataclasses `frozen` para valores.
- `logging` (nunca `print`, salvo salida de CLI como `--probe`).
- Código, comentarios, mensajes y docs en **español**.
- Línea máx. 100; ruff con reglas `E,F,I,UP,B`.
- Tests del núcleo con fakes; nada de tests que dependan de ventanas reales.

## Verificación manual (Windows)
1. `--probe` debe listar la pestaña de Claude Code.
2. Arrancar `python -m paste_photo`, ir a otra app, Win+Shift+S → en el prompt de
   Claude aparece `[Image #N]` sin enviarse y el foco vuelve a la app original.
3. Copiar texto no debe hacer nada; sin Claude abierto, solo un log.
⚠️ Si lo ejecutas desde una sesión de Claude Code, la imagen se pegará en **esa** sesión.

## No tocar sin motivo
- `platforms/windows/focus.py`: `AttachThreadInput` + tecla virtual sin asignar (0xE8) para
  poder hacer `SetForegroundWindow`. **Nunca** usar Alt: abre menús en navegadores.
- `paste_keys = "alt+v"`: en Windows Terminal, Ctrl+V solo pega texto.
