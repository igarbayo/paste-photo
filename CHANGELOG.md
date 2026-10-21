# Changelog

Todos los cambios relevantes de este proyecto se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/)
y el proyecto se adhiere a [Semantic Versioning](https://semver.org/lang/es/).

## [Unreleased]

## [0.4.5] - 2026-10-21

### Fixed
- **La notificación decía "no hay ningún Claude abierto" aunque lo hubiera.** Si PastePhoto
  encontraba Claude pero el pegado fallaba (p. ej. en `PastePhoto.app` con Terminal, sin el
  permiso de Accesibilidad o de Automatización, que se pierden al actualizar una app sin
  firmar), avisaba como si no hubiera ninguno. Ahora dice dónde falló y por qué: "no se pudo
  pegar en Terminal: falta el permiso de Accesibilidad (Ajustes del Sistema → …)". `NotPasted`
  lleva `failures` (destino, error) y `osascript` traduce el error -1743 a qué permiso falta.

## [0.4.4] - 2026-10-21

### Fixed
- **Ya no se pega en páginas de claude.ai que no son un chat.** Con un artifact abierto (p. ej.
  un documento, `/artifact/...` o `/code/artifact/...`) como última pestaña usada, la captura
  iba a él: tiene un editor como el del prompt, así que el pegado "funcionaba" sin llegar a
  ningún chat. Ahora `browser_extension`, `browser` (Windows) y `macos_browser` solo usan
  pestañas cuya URL es un chat (`/new`, `/chat/`, `/project/`, `/code`, `/design` y la raíz;
  nunca con `artifact` en la ruta) y descartan el resto de claude.ai (artifacts, recientes,
  proyectos, ajustes, chats compartidos...). Nueva opción `chat_url_regex` en esos destinos.
  `linux_browser` (solo título de ventana) no puede distinguirlas.

## [0.4.3] - 2026-10-21

### Added
- **macOS: PastePhoto.app** (Apple silicon, Experimental). La release incluye
  `PastePhoto-X.Y.Z-macos-arm64.dmg`: se arrastra a Aplicaciones y se abre con doble clic; vive
  en la barra de menús (`LSUIElement`, sin icono en el Dock). Sin firma de desarrollador ni
  notarización (firma ad hoc): la primera vez hay que pulsar "Abrir igualmente" en Ajustes →
  Privacidad y seguridad o quitar la cuarentena con `xattr`. `packaging/build.py` construye
  el `.app` y, con `--dmg`, la imagen de disco en macOS, con prueba de humo; CI la construye
  en cada push (`build-macos`, que además la abre con `open` como un doble clic y comprueba
  que sigue viva) y `release.yml` la publica (job `macos`). Desde la app, el
  inicio automático, el host de la extensión, `doctor` y el aviso "ya se está ejecutando"
  (diálogo nativo) usan los ejecutables del `.app`, y se añade el PATH de Homebrew para
  encontrar `tmux`, `kitty` y `wezterm` al abrirla desde Finder.

### Changed
- CI: `actions/upload-artifact` v5 → v6 y `actions/download-artifact` v5 → v7 (Node 24),
  para quitar el aviso de Node 20 obsoleto.

## [0.4.2] - 2026-10-21

### Fixed
- **macOS, Terminal.app**: con Claude Code en varias pestañas, tras pulsar una (p. ej. la 3.ª)
  e irse a otra app, la captura se pegaba en otra pestaña (la 1.ª). Las pestañas de Terminal
  son pestañas nativas de macOS: AppleScript ve cada una como una ventana con su única pestaña
  seleccionada y "visible", así que todas empataban y ganaba la primera de la lista. Ahora
  gana la pestaña que tuvo el foco más recientemente (cada pestaña es una ventana del SO con
  su propio `CGWindowID`) y, si PastePhoto no la vio, la que está en pantalla.

## [0.4.1] - 2026-10-21

### Fixed
- **macOS**: con varios Claude Code abiertos a la vez en iTerm2 o Terminal.app, PastePhoto
  elegía uno cualquiera (todos comparten la misma ventana del SO para la prioridad por uso
  reciente) y podía cambiar de pestaña para pegar en otro. Ahora gana la sesión que tienes a
  la vista: la pestaña seleccionada (en iTerm2, el panel con el foco) de la ventana delantera
  de la app, luego las de las demás ventanas por orden. Nuevo punto de extensión
  `EnvTerminalTarget.session_rank()`.
- **Linux y macOS**: lo mismo con varios Claude en **tmux**, **kitty** o **WezTerm** (todos
  sus paneles compartían ventana del SO, o ninguna en tmux). Ahora gana el panel a la vista:
  tmux, el panel activo de la ventana activa de una sesión conectada (y, entre sesiones, la
  del cliente con la última tecla); kitty, la ventana con el foco y luego la activa de cada
  pestaña activa (`kitty @ ls`); WezTerm, el panel con el foco de la GUI y luego el activo de
  cada pestaña (`wezterm cli list`/`list-clients`); Konsole, la pestaña actual de su ventana
  (D-Bus `currentSession`). En Windows, Windows Terminal y los navegadores ya preferían la
  pestaña seleccionada. Orca sigue sin desempate entre sus terminales.
- **tmux**: sus paneles cuelgan del servidor de tmux, sin ventana, así que en la prioridad
  por uso reciente perdían siempre frente a otro Claude aunque fuera el que estabas usando.
  Ahora cuentan como la ventana del terminal donde está conectado el cliente de su sesión
  (en macOS, la de iTerm2 o Terminal usada más recientemente).
- **Terminales con todas sus ventanas en un proceso** (GNOME Terminal, Ptyxis, Tilix,
  kitty, Konsole, WezTerm...): un Claude contaba como la primera ventana del proceso, no la
  suya. `linux_terminal` solo miraba esa primera ventana: con Claude en otra ventana de GNOME
  Terminal no lo encontraba o pegaba en la que no era. Ahora `linux_terminal` busca entre
  todas las ventanas del terminal las que tienen el título de Claude; kitty usa la ventana del
  SO exacta de cada panel (`platform_window_id`) y el resto, la usada más recientemente.

### Changed
- README: en Windows sin la extensión, PastePhoto trae al frente un momento la pestaña de
  Claude del navegador y vuelve a la tuya; con la extensión no cambia de pestaña. También
  se aclara que la extensión solo cubre claude.ai en el navegador, no las terminales.

## [0.4.0] - 2026-10-20

### Added
- **macOS**: PastePhoto corre en la barra de menús de macOS en los mismos casos
  que en Windows y Linux. Familia de plataforma propia (`platforms/macos/`, pyobjc):
  capturas del portapapeles (`NSPasteboard`) y de la carpeta de capturas (Cmd+Shift+4; se
  copian al portapapeles para que Claude Code las lea), ventanas y foco con la API de
  Accesibilidad, teclas con Quartz e inicio al iniciar sesión con un LaunchAgent. Nuevos
  destinos: `iterm2` (AppleScript, sin foco), `terminal_app` (Terminal.app: selecciona la
  pestaña por su tty), `macos_terminal` (Ghostty, Alacritty, Warp...: ventana + Ctrl+V) y
  `macos_browser` (Safari y Chromium por AppleScript, también pestañas de fondo; Firefox y
  demás por el título de la ventana; Cmd+V). `tmux`, `kitty`, `wezterm`, `orca` y
  `browser_extension` también funcionan en macOS; `setup browser` registra el host nativo en
  `~/Library/Application Support`. `paste-photo doctor` comprueba los permisos de
  Accesibilidad y Automatización. Instalación con pipx.
- ADR 0003 (`docs/adr/0003-macos.md`): decisiones del soporte de macOS.
- Metadatos públicos con macOS: descripción y *topics* del repositorio en GitHub (`macos`,
  `iterm2`, `safari`), `keywords`/`classifiers` de `pyproject.toml`, imagen social
  regenerada ("Windows · macOS · Linux", Safari) y `CONTRIBUTING.md`.
- CI en macOS: tests en `macos-latest` e integración real (portapapeles, carpeta de capturas,
  captura → tmux con un Claude falso, AppleScripts compilados contra Terminal, Safari y Chrome).
- Destino `orca` (Windows y Linux): Claude Code en las terminales de
  [Orca](https://github.com/stablyai/orca) recibe las capturas por su CLI
  (`orca terminal send`), sin foco y aunque la terminal no sea la visible. Comprobación de
  Orca en `paste-photo doctor` y bloque en `default_config.toml`.
- La imagen se pega donde está el cursor del prompt: en el navegador, la extensión recuerda
  la última posición del cursor en el prompt de claude.ai (`cursor.js`) y, si nunca estuvo
  ahí, pega al final.
- **Firefox** (Windows y Linux): la extensión del navegador funciona también en Firefox y
  LibreWolf (`.xpi` generado a partir de la de Chromium). `setup browser` registra el host
  nativo para ellos (`~/.mozilla`, `~/.librewolf`; `HKCU\Software\Mozilla` y `\LibreWolf`) y
  deja el `.xpi`; la release lo publica, firmado en addons.mozilla.org si hay credenciales.
- Destino `browser` (Windows, sin extensión): también Firefox (y LibreWolf, Waterfox, Floorp
  y Zen, sin probar).
- Destino `linux_browser`: claude.ai en cualquier navegador de Linux sin la extensión
  (GNOME Web, Falkon, qutebrowser...): enfoca su ventana y pulsa Ctrl+V.

- Imagen de marca del repositorio: logo y cabecera del README con insignias (versión, CI,
  licencia, plataformas) e imagen social de GitHub (`docs/assets/`), generados por código
  desde el icono con `packaging/make_brand.py`.
- Demo animada en el README (`docs/assets/demo.gif`): grabada en Windows con PastePhoto y
  Claude Code reales (captura con Win+Shift+S); el rectángulo de Recortes se redibuja en el GIF.
  Se vuelve a grabar con `packaging/demo/demo.py`.

### Changed
- Imagen social (`docs/assets/social-preview.png`) sin la franja naranja del borde
  izquierdo (`packaging/make_brand.py`).
- El producto se llama **PastePhoto** en todo lo visible (README, bandeja, mensajes,
  instalador y accesos directos, lanzador de Linux, extensiones, winget, imágenes de marca).
  `paste-photo` sigue siendo el id técnico: comando, ejecutables, paquetes, rutas de
  configuración, inicio automático e id de winget no cambian. El instalador borra los
  accesos directos con el nombre anterior.
- Extensión: el `paste` se lanza en el mundo de la página (`world: "MAIN"`) y el cursor se
  coloca antes en el mundo aislado; necesario en Firefox, igual en Chromium.
- `title_regex` por defecto de `browser`: admite la raya larga de los títulos de Firefox
  ("… - Claude — Mozilla Firefox").
- Metadatos públicos al día con lo que hace hoy: descripción y *topics* del repositorio en
  GitHub, `description`/`keywords`/`classifiers` de `pyproject.toml`, descripción y etiquetas
  de winget, descripción del `.deb` y `CONTRIBUTING.md` (Firefox, Orca, Linux).
- macOS deja de ser "Experimental": probado en un Mac real. README (tabla de plataformas,
  instalación), `CONTRIBUTING.md`, ADR 0003, `CLAUDE.md` y descripción del repositorio en
  GitHub sin "(experimental)".
- README: cómo abrir PastePhoto con un icono. En Windows, el instalador añade el acceso
  directo del menú Inicio y, si se elige, el del escritorio; en Linux, el `.deb` lo añade al
  menú de aplicaciones y con pipx se arranca desde la terminal.

### Fixed
- macOS (Terminal): tras pegar, la ventana de Terminal vuelve a mostrar tu pestaña y no la de
  Claude. Con las pestañas nativas de macOS, AppleScript ve cada pestaña como una ventana con
  una sola pestaña, así que la restauración nunca se ejecutaba; ahora se guarda la ventana
  delantera de Terminal antes de seleccionar la de Claude y se vuelve a poner delante.
- macOS: las capturas guardadas como archivo se detectan también en la carpeta elegida en
  Cmd+Shift+5 → Opciones → Guardar en (`location-last` de `com.apple.screencapture`, p. ej.
  `~/Desktop/Screenshots`); antes solo se leía `location` y, si no estaba, se vigilaba el
  escritorio. Se vigilan las dos (sin repetir) y se vuelven a leer cada 5 s, así que cambiar
  de carpeta no exige reiniciar PastePhoto. `doctor` muestra las carpetas vigiladas.
- Extensión de navegador: la imagen ya no va al principio del prompt cuando el cursor no
  estaba en él (p. ej. tras hacer clic en otra parte de la página).
- Destino `browser` (Windows, sin extensión): ya no mueve el cursor si el prompt tiene el
  foco; si no lo tiene, lo enfoca y se respeta la última posición del cursor.
- macOS y Linux: se detecta Claude Code instalado con el instalador nativo (`~/.local/bin/claude`
  → `versions/<versión>`, proceso llamado como la versión); antes solo se reconocía la
  instalación por npm y en Terminal no se pegaba nunca. La app de escritorio Claude.app y el
  puente de Claude in Chrome (`claude --chrome-native-host`) ya no cuentan como Claude Code.
  Solo se descarta Claude.app, no cualquier bundle `.app` (el Python de python.org se
  relanza desde `Python.app` y dejaba fuera la integración de macOS en CI).

## [0.3.0] - 2026-10-20

### Added
- **Linux**: soporte para cualquier terminal y cualquier navegador Chromium, en X11, GNOME
  Wayland y KDE Wayland. La sesión se detecta sola (`platforms/linux/session.py`).
- **Extensión de navegador** (Chromium MV3, Windows y Linux) + host de native messaging
  (`paste-photo-native-host`): pega en claude.ai (Chat, Code, Design) sin foco ni teclas,
  también en pestañas de fondo y en capturas de varios MB (mensajes troceados). Destino
  `browser_extension`.
- Destinos de terminal con IPC, sin foco: `tmux` (`send-keys`), `kitty` (control remoto),
  `wezterm` (`wezterm cli`) y `konsole` (D-Bus). El panel exacto se obtiene del entorno del
  proceso `claude`; tmux tiene prioridad si va dentro de otro terminal.
- Destino `linux_terminal` para cualquier otro terminal: ventana del terminal → foco →
  Ctrl+V, solo si la pestaña de Claude es la activa.
- Sistemas de ventanas de Linux: X11 (python-xlib: EWMH + XTEST, con alternativas para
  gestores sin EWMH y PID por XRes), GNOME Shell (extensión propia `setup gnome`) y KWin
  (scripts por D-Bus + portal RemoteDesktop).
- Capturas en Linux: portapapeles X11 (XFixes), `wl-paste --watch` (KDE, wlroots) y carpeta
  de capturas (GNOME Wayland).
- `paste-photo doctor`: diagnóstico de sesión, herramientas, extensión, procesos de Claude y
  bandeja, con cómo arreglar cada problema.
- `paste-photo setup browser` (registra el host nativo en Chrome, Chromium, Edge, Brave,
  Vivaldi y Opera) y `paste-photo setup gnome`.
- Inicio automático en Linux (`~/.config/autostart`, XDG).
- Paquete **.deb** (`packaging/linux/build_deb.py`) e instalación con **pipx**.
- `paste-photo-native-host.exe` en el instalador de Windows.
- CI: integración real en Linux con Xvfb + Openbox + xterm + tmux, y build + instalación del
  `.deb`. La release publica también el `.deb` y el zip de la extensión.
- Puerto `WindowSystem` y eventos de captura con la imagen PNG (carga perezosa).

### Changed
- `TargetStrategy.paste(handle, shot)` recibe la captura.
- La prioridad "recent" usa también el último uso que conoce el destino (`last_used`), p. ej.
  la pestaña activa del navegador, y un reloj de pared.
- Cada destino declara sus sistemas operativos y los de otros SO se omiten: una sola
  `default_config.toml` para Windows y Linux.
- "Iniciar con Windows" se llama "Iniciar al iniciar sesión" en Linux.

### Fixed
- El teclado X11 abre una conexión por pulsación y envía cada evento sincronizado: con una
  conexión larga, un cambio del mapa de teclado hacía que Ctrl no se aplicara.
- Sin notificaciones en bandejas que no las admiten, en vez de registrar un error cada vez.

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
- El envío a winget falla con un mensaje claro si el secreto `WINGET_TOKEN` está vacío.

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

[Unreleased]: https://github.com/igarbayo/paste-photo/compare/v0.4.5...HEAD
[0.4.5]: https://github.com/igarbayo/paste-photo/compare/v0.4.4...v0.4.5
[0.4.4]: https://github.com/igarbayo/paste-photo/compare/v0.4.3...v0.4.4
[0.4.3]: https://github.com/igarbayo/paste-photo/compare/v0.4.2...v0.4.3
[0.4.2]: https://github.com/igarbayo/paste-photo/compare/v0.4.1...v0.4.2
[0.4.1]: https://github.com/igarbayo/paste-photo/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/igarbayo/paste-photo/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/igarbayo/paste-photo/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/igarbayo/paste-photo/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/igarbayo/paste-photo/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/igarbayo/paste-photo/releases/tag/v0.1.0
