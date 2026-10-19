# ADR 0001 — Python y arquitectura de puertos y adaptadores

- **Estado:** aceptada
- **Fecha:** 2026-10-19

## Contexto
La app debe pegar capturas en Claude Code. Empieza en Windows + Windows Terminal, pero tiene
que extenderse a macOS y Linux, y a la app de escritorio, el navegador y VS Code, sin
reescribir lo existente.

## Decisión
- **Lenguaje: Python.** Bindings maduros para cada SO (pywin32/uiautomation, pyobjc,
  xdotool/wl-clipboard), fácil de distribuir (pipx/PyInstaller). El trabajo es E/S del SO,
  así que un lenguaje compilado no aporta rendimiento relevante.
- **Arquitectura hexagonal:** un núcleo (`core/`) sin dependencias de SO habla con el mundo
  mediante puertos (`typing.Protocol`).
- **Patrones:**
  - *Abstract Factory* (`platforms/factory.py`): una familia de adaptadores por SO.
  - *Strategy* + *Registry* (`targets/`): cada destino sabe localizar y pegar; se añaden
    con un decorador.
  - *Chain of Responsibility* (`Orchestrator`): destinos en orden de prioridad.
  - *Observer* (`ScreenshotSource`): desacopla detectar de pegar.
  - *Memento* (`preserve_focus`): restaurar la ventana previa.

## Consecuencias
- ➕ Añadir un SO o un destino no toca el núcleo; el núcleo se testea en cualquier SO.
- ➕ Las dependencias de SO son opcionales por marcador y se importan de forma perezosa.
- ➖ Algo más de estructura que un script único.
- ➖ La detección en terminal depende del título de pestaña que pone Claude Code
  (mitigado con `title_regex` configurable y `--probe`).
