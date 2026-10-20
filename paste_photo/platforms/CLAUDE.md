# platforms/ — adaptadores por sistema operativo

Recuerda la regla obligatoria del CLAUDE.md raíz: todo cambio lleva entrada en `CHANGELOG.md`.

Abstract Factory: `factory.get_platform_factory()` elige según `sys.platform` y devuelve una
factoría que crea la familia coherente: `ScreenshotSource`, `FocusManager`, `Keyboard`,
`Autostart`, `WindowSystem` (o `None`) y `worker_context()` (preparación por hilo).

| SO | Estado |
|---|---|
| Windows | ✅ `windows/` (pywin32 + UI Automation en los destinos) |
| Linux | ✅ `linux/`: X11 probado en real; GNOME/KDE Wayland implementados, sin probar en real |
| macOS | ✅ `macos/` (pyobjc): probado en un Mac real; CI real: portapapeles, carpeta y tmux |

## Receta: añadir/completar un SO
1. En `platforms/<so>/` implementa los puertos (contratos en `core/CLAUDE.md`).
2. Sustituye los `NotImplementedError` de `<So>Factory` por las instancias reales.
3. Añade dependencias en `pyproject.toml` **con marcador** (`; sys_platform == 'darwin'`).
4. Importa librerías del SO solo dentro de `platforms/<so>/` (nunca en `core/`).
5. Declara en los destinos que funcionen ahí `platforms=(..., "<so>")`.
6. Actualiza la tabla de arriba, el README, `doctor.py` y el CHANGELOG (`Added`).

## macOS (`macos/`)
| Puerto | Implementación |
|---|---|
| Capturas | `MacScreenshotSource`: sondeo de `NSPasteboard.changeCount` (250 ms; `public.png`, si no `public.tiff`; nada si hay `public.file-url`) **y** archivos nuevos de las carpetas de capturas (`screenshot_folders()`: `location-last` y `location` de `com.apple.screencapture`, releídas cada 5 s; si no hay ninguna, el escritorio; nombre por prefijos de cada idioma o `... name`) |
| Ventanas | `MacWindowSystem`: pids con ventanas por `CGWindowListCopyWindowInfo`; ventanas y títulos por AX (`AXWindows`, `AXTitle`); id = `CGWindowID` con `_AXUIElementGetWindow` (privada, por ctypes) o id sintético |
| Foco | `MacFocus`: Memento = ventana con el foco (AX `AXFocusedApplication` → `AXFocusedWindow`), o `-pid` si la app no tiene ventana; activar = `AXRaise` + `AXFrontmost` |
| Teclado | `MacKeyboard`: `CGEventPost` con fuente privada (`kCGEventSourceStatePrivate`); keycodes ANSI |
| Autoarranque | `LaunchAgentAutostart`: `~/Library/LaunchAgents/io.github.igarbayo.paste-photo.plist` |

Permisos: **Accesibilidad** (foco, teclas, títulos) y **Automatización** (AppleScript de los
destinos `iterm2`, `terminal_app`, `macos_browser`; macOS lo pide por app la primera vez).

### Trampas de macOS
- `NSWorkspace.frontmostApplication`/`runningApplications` no se actualizan sin bucle de
  eventos en el hilo principal (modo `run`, `--probe`): por eso AX y CGWindowList.
- Activación cooperativa (macOS 14+): `NSRunningApplication.activate` desde una app de fondo
  puede no hacer nada; `AXFrontmost` sí (con Accesibilidad). Queda como respaldo.
- Hilos largos con AppKit/AX: cada iteración en su `objc.autorelease_pool()` (no hay pool
  automático en hilos de Python).
- La carpeta elegida en Cmd+Shift+5 → Opciones → Guardar en va a `location-last`, **no** a
  `location` (que solo existe si alguien hizo `defaults write ... location`). Visto en un Mac
  real: capturas en `~/Desktop/Screenshots` que no se detectaban vigilando solo el escritorio.
- Las capturas con Cmd+Shift+4 son **solo archivo**: se copian al portapapeles (Claude Code
  lee de ahí con Ctrl+V) y el `changeCount` propio se ignora. macOS escribe el archivo al
  desaparecer la miniatura flotante (~5 s).
- El permiso de Accesibilidad es del **proceso responsable**: lanzado desde Terminal, lo
  hereda de Terminal; con el LaunchAgent, el binario de Python (`doctor` muestra la ruta).
- launchd arranca con PATH mínimo: el LaunchAgent guarda el PATH actual + Homebrew.
- La bandeja (pystray darwin) corre el bucle de AppKit en el hilo principal; `hide_dock_icon()`
  (`ui/_system.py`) la deja como app de la barra de menús (`ActivationPolicyAccessory`).

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
