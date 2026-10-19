# platforms/ — adaptadores por sistema operativo

Recuerda la regla obligatoria del CLAUDE.md raíz: todo cambio lleva entrada en `CHANGELOG.md`.

Abstract Factory: `factory.get_platform_factory()` elige según `sys.platform` y devuelve una
factoría que crea la familia coherente: `ScreenshotSource`, `FocusManager`, `Keyboard`,
`Autostart`, `WindowSystem` (o `None`) y `worker_context()` (preparación por hilo).

| SO | Estado |
|---|---|
| Windows | ✅ `windows/` (pywin32 + UI Automation en los destinos) |
| Linux | ✅ `linux/`: X11 probado en real; GNOME/KDE Wayland implementados, sin probar en real |
| macOS | ⏳ stub `macos/__init__.py` |

## Receta: añadir/completar un SO
1. En `platforms/<so>/` implementa los puertos (contratos en `core/CLAUDE.md`).
2. Sustituye los `NotImplementedError` de `<So>Factory` por las instancias reales.
3. Añade dependencias en `pyproject.toml` **con marcador** (`; sys_platform == 'darwin'`).
4. Importa librerías del SO solo dentro de `platforms/<so>/` (nunca en `core/`).
5. Declara en los destinos que funcionen ahí `platforms=(..., "<so>")`.
6. Actualiza la tabla de arriba, el README, `doctor.py` y el CHANGELOG (`Added`).

Pista **macOS**: portapapeles con `NSPasteboard.changeCount` (sondeo ~250 ms) y tipo
`public.png`; foco con `NSRunningApplication.activateWithOptions_`; teclas con
`CGEventCreateKeyboardEvent` (permiso de Accesibilidad). tmux/kitty/WezTerm ya declaran macOS.

## Linux (`linux/`)
La familia depende de la **sesión** (`session.detect()`, forzable con `PASTE_PHOTO_BACKEND`):

| Sesión | Backend | Ventanas (`WindowSystem`) | Teclado | Capturas |
|---|---|---|---|---|
| X11 | `x11` | python-xlib: EWMH; si no hay `_NET_CLIENT_LIST`, árbol de ventanas; PID por `_NET_WM_PID` o XRes | XTEST | `X11ClipboardSource` (XFixes + xclip) |
| GNOME Wayland | `gnome` | extensión de GNOME Shell propia (D-Bus `io.github.igarbayo.PastePhoto`) | `SendKeys` de la extensión (solo atajos de pegado) | `ScreenshotFolderSource` |
| KDE Wayland | `kde` | scripts de KWin cargados por D-Bus, devuelven datos con `callDBus` | portal RemoteDesktop (permiso una vez, `restore_token`) | `WlPasteWatchSource` |
| Otro Wayland con XWayland (wlroots, WSLg) | `x11` | solo apps XWayland | XTEST | `wl-paste --watch` si hay data-control |
| Sin control | `none` | `None` | `NullKeyboard` | según lo disponible |

Sin `WindowSystem`, siguen funcionando la extensión del navegador y los terminales con IPC.

### Trampas de Linux (todas vistas en pruebas reales)
- **XTEST**: abrir **una conexión por pulsación** y sincronizar cada evento con pausa (como
  xdotool). Con una conexión larga el mapa de teclado queda viejo (no se procesa
  `MappingNotify`) y Ctrl deja de aplicarse: llegaba `v` en vez de `^V`.
- python-xlib: los métodos de extensiones son del **display** y no salen en `dir()`
  (`d.xfixes_select_selection_input(root, sel, mask)`); `set_error_handler` evita que un
  `BadWindow` (ventana cerrada a mitad de consulta) ensucie stderr.
- **WSLg** no es un buen banco de pruebas de foco: su compositor ignora `_NET_ACTIVE_WINDOW`
  entre ventanas X. Usar Xvfb + Openbox (como `tests/integration`).
- GNOME no implementa data-control: `wl-paste --watch` sale con error → se usa la carpeta de
  capturas (`default_screenshot_dirs()`; nunca la carpeta Imágenes entera).
- jeepney (D-Bus): registrar el filtro **antes** de la llamada cuya respuesta llega por otro
  mensaje (KWin `Report`, portal `Response`), o jeepney descarta el mensaje.
- Inicio automático: `~/.config/autostart/paste-photo.desktop` con la orden de
  `app.launch_command()` (`PASTE_PHOTO_LAUNCH` en el .deb, script de pipx, si no `python -m`).

## Trampas de Windows
- `SetForegroundWindow` falla si el proceso no recibió la última entrada. `focus.activate()`
  primero se une a la cola de entrada de la ventana activa (`AttachThreadInput`) y, si no
  basta, pulsa una tecla virtual **sin asignar** (0xE8). Nunca Alt: un Alt suelto llega a la
  ventana destino y abre la barra de menús en navegadores/apps (verificado en pruebas).
- Una ventana puede quitarse el foco a sí misma después de restaurarlo (p. ej. Edge durante
  un inicio de sesión); no es un fallo de paste-photo.
- El portapapeles puede estar abierto por otro proceso: `_read_image` reintenta.
- Win+Shift+S puede disparar varios `WM_CLIPBOARDUPDATE` con la misma imagen: lo absorbe
  la deduplicación del Orchestrator.
- Solo se reacciona a `CF_DIB` (convertido a PNG solo si un destino lo pide, `imaging.py`).
- UI Automation usa COM: el hilo de trabajo lo inicializa con `worker_context()`.
