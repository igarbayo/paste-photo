# ADR 0003: soporte de macOS

- **Estado:** aceptada (experimental hasta probarlo en un Mac real)
- **Fecha:** 2026-10-20

## Contexto
PastePhoto debía funcionar en macOS en los mismos casos que en Windows y Linux: Claude Code en
cualquier terminal y claude.ai en el navegador, con extensión o sin ella, desde la barra de
menús y con inicio al iniciar sesión. macOS no deja ver ni controlar otras apps sin permisos
explícitos (Accesibilidad, Automatización) y no hay un Mac en el equipo de desarrollo.

## Decisión
- **pyobjc** (MIT) para AppKit, Quartz y la API de Accesibilidad; pystray ya lo usaba.
- **Capturas**: sondeo de `NSPasteboard.changeCount` **y** de la carpeta de capturas. Las
  capturas por defecto de macOS (Cmd+Shift+4) solo crean un archivo; se copian al
  portapapeles porque Claude Code lee de ahí al pulsar Ctrl+V.
- **Ventanas y foco**: API de Accesibilidad (títulos, ventana con foco, `AXRaise` y
  `AXFrontmost`) en lugar de `NSWorkspace`/`NSRunningApplication`, que no se actualizan sin
  bucle de eventos y que la activación cooperativa de macOS 14 puede ignorar.
- **Canales sin foco primero** (regla de oro 7): tmux, kitty, WezTerm, Orca (como en Linux) e
  **iTerm2 por AppleScript** (`write text`). Terminal.app no tiene canal sin teclear, así que
  AppleScript solo **selecciona la pestaña** (por `tty`) y se pulsa Ctrl+V.
- **Navegadores sin extensión**: Safari y los Chromium con diccionario de AppleScript dan la
  URL de todas las pestañas (mejor que el título de la ventana de Linux); el resto, por título
  de ventana como `linux_browser`. La extensión funciona igual que en Linux (host nativo en
  `~/Library/Application Support`). Safari no admite la extensión sin una app propia.
- **Inicio**: LaunchAgent del usuario (sin administrador).
- **Distribución**: pipx por ahora. Un `.app` sin firmar ni notarizar choca con Gatekeeper y
  no aporta funciones; queda como siguiente paso (`packaging/CLAUDE.md`).
- **Pruebas sin Mac**: unitarias con fakes en todos los SO y un job de CI en `macos-latest` que
  prueba en real lo que no necesita permisos (portapapeles, carpeta, tmux) y compila los
  AppleScripts con `osacompile` contra las apps reales.

## Consecuencias
- ➕ Sin tocar `core/`: una factoría nueva y cuatro destinos (`iterm2`, `terminal_app`,
  `macos_terminal`, `macos_browser`); los destinos IPC y la extensión solo declaran macOS.
- ➖ Lo que necesita Accesibilidad o Automatización no se puede probar en CI: se marca
  "Experimental" en el README hasta tener pruebas en un Mac real.
- ➖ El permiso de Accesibilidad va al proceso que lanza PastePhoto (Terminal o el Python del
  LaunchAgent), no a una app con nombre propio, hasta que haya un `.app`.
- ➖ `_AXUIElementGetWindow` es una función privada; si desaparece, se usan ids sintéticos.
