# platforms/ — adaptadores por sistema operativo

Recuerda la regla obligatoria del CLAUDE.md raíz: todo cambio lleva entrada en `CHANGELOG.md`.

Abstract Factory: `factory.get_platform_factory()` elige según `sys.platform` y devuelve una
factoría que crea la familia coherente `ScreenshotSource` + `FocusManager` + `Keyboard`.

| SO | Estado |
|---|---|
| Windows | ✅ `windows/` (pywin32) |
| macOS | ⏳ stub `macos/__init__.py` |
| Linux | ⏳ stub `linux/__init__.py` |

## Receta: añadir/completar un SO
1. En `platforms/<so>/` implementa los 3 puertos (contratos en `core/CLAUDE.md`).
2. Sustituye los `NotImplementedError` de `<So>Factory` por las instancias reales.
3. Añade dependencias en `pyproject.toml` **con marcador** (`; sys_platform == 'darwin'`).
4. Importa librerías del SO solo dentro de `platforms/<so>/` (nunca en `core/`).
5. Añade a `config.default_targets()` el destino por defecto de ese SO.
6. Actualiza la tabla de arriba, el README y el CHANGELOG (`Added`).

Pistas:
- **macOS**: portapapeles con `NSPasteboard.changeCount` (sondeo ~250 ms; no hay evento) y tipo
  `public.png`/`public.tiff`; Cmd+Shift+Ctrl+4 copia al portapapeles. Foco con
  `NSRunningApplication.activateWithOptions_`. Teclas con `CGEventCreateKeyboardEvent`.
  Requiere permiso de Accesibilidad.
- **Linux X11**: `xclip -selection clipboard -t TARGETS` / XFixes para eventos; `xdotool`
  para foco y teclas. **Wayland**: `wl-paste --watch`; foco/teclas dependen del compositor
  (`ydotool`, D-Bus de GNOME/KDE) — documentar limitaciones.

## Trampas de Windows
- `SetForegroundWindow` falla si el proceso no recibió la última entrada: por eso
  `focus.activate()` pulsa Alt sintético antes. No quitarlo.
- El portapapeles puede estar abierto por otro proceso: `_read_image` reintenta.
- Win+Shift+S puede disparar varios `WM_CLIPBOARDUPDATE` con la misma imagen: lo absorbe
  la deduplicación del Orchestrator.
- Solo se reacciona a `CF_DIB`; texto u otros formatos se ignoran.
- La ventana del listener es `HWND_MESSAGE` en un hilo propio; `stop()` envía `WM_CLOSE`.
