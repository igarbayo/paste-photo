# targets/ — dónde está Claude y cómo pegar

Recuerda la regla obligatoria del CLAUDE.md raíz: todo cambio lleva entrada en `CHANGELOG.md`.

Strategy + Registry: cada destino es un módulo que registra un *builder*
`(options: Mapping, ctx: TargetContext) -> TargetStrategy` con
`@register_target("tipo", platforms=("linux", ...))` (sin `platforms` = cualquier SO).
`options` es la tabla `[[targets]]` de `config.toml`; `ctx` trae `platform`, `focus`,
`keyboard`, `recency` y `windows` (`WindowSystem` o `None`). Los destinos de otro SO se
omiten solos (`service.build_targets`), así que la config por defecto los lista todos.

| Tipo | SO | Cómo pega | Foco |
|---|---|---|---|
| `browser_extension` | Windows, macOS, Linux | la extensión inyecta un `paste` con el PNG en el editor | no |
| `windows_terminal` | Windows | UI Automation: selecciona la pestaña, **Alt+V** | sí |
| `browser` | Windows | UI Automation (Chromium y Firefox): pestaña + editor (solo enfoca si no lo tenía), Ctrl+V | sí |
| `orca` | Windows, macOS, Linux | `orca terminal send --terminal $ORCA_TERMINAL_HANDLE --text <tecla>` | no |
| `tmux` | Linux, macOS | `tmux -S <socket> send-keys -t <pane> C-v` | no |
| `kitty` | Linux, macOS | `kitty @ --to $KITTY_LISTEN_ON send-text --match id:N ` | no |
| `wezterm` | Linux, macOS | `wezterm cli send-text --no-paste --pane-id N ` | no |
| `konsole` | Linux | D-Bus `org.kde.konsole.Session.sendText("")` | no |
| `linux_terminal` | Linux | `WindowSystem.activate` + **Ctrl+V** (solo si la pestaña de Claude es la activa) | sí |
| `linux_browser` | Linux | ventana de navegador con título de Claude → `activate` + **Ctrl+V** (sin extensión: GNOME Web, Falkon...) | sí |
| `iterm2` | macOS | AppleScript: `write text "\x16" without newline` en la sesión de `ITERM_SESSION_ID` | no |
| `terminal_app` | macOS | AppleScript selecciona la pestaña por `tty` → **Ctrl+V** → vuelve a la pestaña | sí |
| `macos_terminal` | macOS | ventana del terminal con título de Claude → `activate` + **Ctrl+V** (Ghostty, Alacritty, Warp...) | sí |
| `macos_browser` | macOS | Safari/Chromium: AppleScript (todas las pestañas, URL) → **Cmd+V** → vuelve; resto por título de ventana | sí |
| `desktop_app`, `vscode` | — | ⏳ `_pending` | |

Estado real: probados de punta a punta en Linux (WSL + Xvfb/Openbox) tmux, kitty, Konsole,
`linux_terminal` (xterm), `orca` (.deb), `browser_extension` (Chromium y Firefox ESR) y
`linux_browser` (Firefox ESR sin extensión); en Windows `orca`, `browser` (Chrome y Firefox
ESR) y `browser_extension` en Firefox ESR; WezTerm solo con tests unitarios. GNOME Web,
Falkon y qutebrowser: sin probar (mismo mecanismo que `linux_browser` con Firefox).

## Navegadores: qué vía tiene cada uno
| Motor | Navegadores | Extensión (`browser_extension`) | Sin extensión |
|---|---|---|---|
| Chromium | Chrome, Edge, Brave, Vivaldi, Opera, Chromium | sí (descomprimida) | Windows `browser`; Linux `linux_browser` |
| Gecko | Firefox, LibreWolf (Waterfox, Floorp, Zen: sin registro de host) | sí (`.xpi`, firmado para Firefox normal) | Windows `browser`; Linux `linux_browser` |
| WebKit | GNOME Web (Epiphany) | no: sin native messaging | Linux `linux_browser` |
| QtWebEngine | Falkon, qutebrowser, Konqueror | no admiten WebExtensions | Linux `linux_browser` |
| WebKit | Safari (macOS) | no: sería una Safari Web Extension con app propia | macOS `macos_browser` (AppleScript) |

En macOS, Chrome, Edge, Brave, Vivaldi y Chromium usan la extensión o, sin ella,
`macos_browser` por AppleScript; Firefox, Arc, Opera..., la extensión (si la admiten) o la
ventana.

## Posición del cursor: la imagen va donde estaba el cursor
- **Terminales**: se envía solo la tecla de pegado; Claude Code inserta `[Image #N]` en su
  cursor. Nunca escribir texto ni mover el cursor (flechas, Fin...).
- **`browser_extension`**: `cursor.js` (content script, mismo mundo aislado que
  `placeCaret`) guarda la última selección dentro del prompt. `placeCaret` usa la actual si
  está en el prompt, si no esa última, si no el final, y espera 50 ms para que ProseMirror lea
  la selección (`selectionchange` es asíncrono); luego `dispatchPaste` (mundo de la página).
- **`browser` (UIA)**: si el editor ya tiene el foco no se toca; si no, `SetFocus()` y
  ProseMirror restaura su última selección (~20 ms). Un `Ctrl+End` la pisaría. Sin
  extensión no se distingue "nunca tuvo cursor" (va al principio).
- **`linux_browser`**: solo activa la ventana; el navegador devuelve el foco al elemento que
  lo tenía. Si no era el prompt, el `paste` cae fuera y no se inserta (sin AT-SPI no se puede
  enfocar el editor).
- Pruebas: página con ProseMirror real (`esm.sh`, `role="textbox"` para que UIA lo vea como
  `EditControl`); en Chromium con `--load-extension`, **perfil nuevo** en cada prueba: el
  service worker de la extensión queda en caché aunque cambie el archivo.

## Firefox por UI Automation (`browser`, Windows)
- Ventana `MozillaWindowClass`; pestañas `TabItemControl`; URL en el `ComboBoxControl`
  `AutomationId="urlbar-input"`; el prompt es `EditControl` con la clase CSS en `ClassName`.
- Firefox devuelve `ClassName` **vacío** hasta que se lee otra propiedad del elemento (lo crea
  al pedírsela): `_class_name()` pide `AutomationId` y vuelve a leer. Además el árbol se monta
  poco a poco tras la primera consulta: `_before_paste` reintenta hasta `EDITOR_WAIT_S`. Hacen
  falta las dos cosas (probado: sin el reintento, la primera captura fallaba a veces).
- Firefox expone también los documentos de las pestañas de fondo: el editor válido es el que
  no está `IsOffscreen` (si no, se pegaría en otra pestaña).
- Títulos de ventana con raya larga: "… - Claude — Mozilla Firefox" (`DEFAULT_TITLE_REGEX`).

## Destinos de terminal en Linux: el entorno del proceso manda
`_processes.claude_processes()` encuentra los `claude` (nombre o `@anthropic-ai/claude-code`
en la línea de órdenes) y lee su **entorno**, que delata el panel exacto: `TMUX`+`TMUX_PANE`,
`KITTY_WINDOW_ID`+`KITTY_LISTEN_ON`, `WEZTERM_PANE`, `KONSOLE_DBUS_SERVICE`+`KONSOLE_DBUS_SESSION`.
- Base común `_env_terminal.EnvTerminalTarget`: cada terminal solo define `describe()` y
  `send_ctrl_v()`.
- **tmux manda**: si `TMUX` está, los terminales exteriores (kitty, WezTerm, Konsole) ignoran
  ese proceso; si no, su Ctrl+V iría al panel activo de tmux, no al de Claude.
- `linux_terminal` solo atiende procesos que **no** cubre ningún IPC (`handled_by_ipc`).
- La ventana de un proceso = ventanas del ancestro más cercano que tiene alguna
  (`owner_windows`); si son varias (GNOME Terminal, kitty, Konsole y WezTerm tienen todas en un
  proceso), `window_of()` toma la usada más recientemente (`most_recent`). Cada destino puede
  cambiarlo: Orca (PTY del daemon) y iTerm2, cualquier ventana de la app; tmux, la ventana del
  terminal del cliente conectado a la sesión del panel (`client_pid`; si sus ancestros no
  tienen ventana, la app de su `TERM_PROGRAM`); kitty, la ventana exacta
  (`platform_window_id` de `kitty @ ls`). `linux_terminal` y `macos_terminal` miran todas las
  ventanas del terminal con título de Claude, no solo la primera.
- Varios Claude en la misma ventana del SO empatan en la recencia. Desempata
  `session_rank()` (pid → tupla, menor = más a la vista; se llama antes de `window_of()` y
  puede dejarle datos): tmux `list-panes -a` + `list-clients` (`client_activity`), kitty
  `@ ls` (`is_focused`, `is_active`), WezTerm `cli list` + `cli list-clients`
  (`focused_pane_id`), Konsole D-Bus `currentSession` de `KONSOLE_DBUS_WINDOW`. Si la
  consulta falla, sin desempate. Orca: `orca terminal list --json
  --include-visual-layouts` (`activeTabId` del grupo, `activeLeafId` de la pestaña; sigue los
  clics, comprobado en 1.4.237 en macOS); entre worktrees distintos, sin desempate. Lo que solo desempata (AppleScript, D-Bus) no se consulta con un único
  Claude.

## Orca (`orca.py`, Windows, macOS y Linux)
- Orca exporta `ORCA_TERMINAL_HANDLE` (y `ORCA_CLI_COMMAND`) a sus terminales; está en
  `IPC_ENV_MARKERS`, así que `linux_terminal` no lo duplica.
- CLI: `orca.exe` (Windows, `%LOCALAPPDATA%\Programs\orca\resources\bin`; no `orca.cmd`,
  cmd.exe reinterpreta el texto), `orca-ide` en Linux (`orca` es el lector de pantalla de
  GNOME) y `orca` en macOS (`Orca.app/Contents/Resources/bin`, sin probar; manda
  `ORCA_CLI_COMMAND`). Opción `cli` para fijarla.
- Bytes: `\x1bv` (Alt+V) en Windows, `\x16` en Linux (`paste_text`). Sin `--enter`.
- Recencia: cualquier ventana del proceso `orca.exe`/`orca-ide` (la usada más recientemente).
  Todas sus terminales empatan ahí: desempata la pestaña seleccionada (`session_rank`).

## macOS (`iterm2`, `terminal_app`, `macos_terminal`, `macos_browser`)
- `TERM_PROGRAM` (lo fija el terminal más interno: `iTerm.app`, `Apple_Terminal`, `tmux`,
  `ghostty`...) decide el destino; `ITERM_SESSION_ID`/`TERM_SESSION_ID` se heredan si se abre
  otro terminal desde iTerm2/Terminal, así que no bastan.
- AppleScript con `osascript -` y datos por `argv` (`_applescript.py`). Dentro de un `tell`
  a Terminal o Chrome, `tab` es su clase "pestaña", **no** el tabulador: los separadores se
  crean fuera (`character id 9`). Las palabras de cada app se resuelven al compilar: el
  bundle id va literal en el texto (nunca una variable) y nunca se usa `tell` con una app
  que no esté abierta (la abriría).
- Las sesiones de iTerm2 cuelgan de `iTermServer` y todas las ventanas de Terminal son del
  mismo proceso: la recencia usa la ventana de la app usada más recientemente, así que todos
  sus Claude empatan. Desempata `session_rank()` (un `LIST_SCRIPT` por AppleScript, solo si hay
  más de un Claude): primero la sesión que se ve (pestaña seleccionada / `current session`),
  luego el índice de su ventana (1 = la delantera). Sin permiso de Automatización, sin
  desempate. Antes se pegaba en el primero que listara psutil y Terminal cambiaba de pestaña.
- Terminal.app con pestañas nativas: cada pestaña es una ventana con una pestaña siempre
  `selected` (y `visible` aunque esté detrás), así que eso no desempata. `LIST_SCRIPT` da
  también el `id` de la ventana, que es su `CGWindowID` (el de `screencapture -l` y de AX):
  primero la recencia de esa ventana (la última pestaña pulsada), luego si está en pantalla
  (`CGWindowListCopyWindowInfo` en pantalla: las de detrás de un grupo no lo están) y el índice.
- Terminal.app con pestañas nativas de macOS: AppleScript ve cada pestaña como una ventana
  con una sola pestaña (`count of tabs` = 1). Para volver a tu pestaña se reordena la
  ventana (`set index of window id ... to 1`), no `selected of tab`. Limitación: si estabas
  en otra app y la ventana delantera de Terminal es de otro grupo, no se sabe qué pestaña se
  veía en el grupo de Claude (AppleScript no da los grupos).
- `macos_browser`: la ventana del SO de una ventana de AppleScript = la de AX cuyo título
  empieza por el de su pestaña activa. Si la Automatización falla, ese navegador pasa a la vía
  por título.
- CI compila los scripts con `osacompile` (`tests/integration/test_macos.py`): un error de
  sintaxis o de vocabulario se ve sin un Mac.

## Teclas para pegar imágenes (fuente: docs oficiales, *Interactive mode*)
Elige `paste_keys` según **dónde corre Claude**, no según el destino:

| Dónde | Claude Code en terminal | claude.ai en navegador |
|---|---|---|
| Windows (WT, PowerShell…) | **`alt+v`** (Ctrl+V lo captura la terminal: solo texto) | `ctrl+v` |
| WSL | **`alt+v`** (también Ctrl+V si la terminal no lo intercepta) | — |
| macOS | **`ctrl+v`** (iTerm2 también `cmd+v`) | `cmd+v` |
| Linux | **`ctrl+v`** | `ctrl+v` |

Error frecuente: creer que Alt+V es para macOS/Linux. Es al revés.

## Receta: añadir un destino
1. Crea `targets/<tipo>.py` con una clase que cumpla `TargetStrategy` (`name`, `locate`, `paste`).
   - Si en Windows se basa en **pestañas visibles por UI Automation**, hereda de
     `_win_uia.UiaTabTarget` e implementa solo lo que cambia (ver abajo).
2. Registra un builder con `@register_target("<tipo>", platforms=(...))` y lee las opciones
   con valores por defecto. Si el destino puede trabajar sin foco (IPC, extensión), mejor.
3. Importa librerías de SO **dentro del constructor o de una función** (el módulo se importa
   en todos los SO). Patrón en `browser.py`: `_windows_browser_target()` define la clase.
4. Añade el módulo a `_BUILTIN_MODULES` en `registry.py` (o sustituye su stub `_pending`).
5. Documenta sus opciones (comentadas) en `paste_photo/resources/default_config.toml` y en el README.
6. Tests en `tests/`: lógica pura (regex, puntuación) con nombres **reales** observados.
7. CHANGELOG: `Added`.

## `UiaTabTarget` (Template Method, `_win_uia.py`)
Puntos de extensión:
- `_candidate_windows()` → hwnds a inspeccionar (obligatorio).
- `_rank(hwnd, tab, selected)` → `None` si no es Claude; menor = mejor (por defecto: `title_regex`).
- `_before_paste(handle)` → con la pestaña ya visible; lanza `TabNotReady` para descartarla
  y que se pruebe la siguiente candidata.

Lo común: ordena candidatos (ventana usada más recientemente según `ctx.recency` >
puntuación > pestaña seleccionada > orden), los prueba en
orden, pega con `paste_keys` y **restaura la pestaña seleccionada** de cada ventana tocada.
Lee propiedades UIA con `safe_attr()` y recorre con `_walk()`: los elementos desaparecen a
mitad de recorrido (COMError) cuando la página cambia.

## Reglas para `locate()` y `paste()`
- `locate()` sin efectos visibles: no enfocar, no cambiar de pestaña.
- `paste(handle, shot)`: recibe la captura (`shot.png()` si se necesita la imagen); usa
  `ctx.focus`/`ctx.windows` y `ctx.keyboard` si hace falta foco; **nunca envía Enter**.
- Antes de pegar, verifica que hay un prompt donde pegar; si no, no pegues.
- Si el destino cambia estado interno (pestaña), restáuralo; el foco de ventana lo
  restaura el Orchestrator.

## windows_terminal
- Ventanas de clase `CASCADIA_HOSTING_WINDOW_CLASS`; pestañas = `TabItemControl`.
- Claude Code titula la pestaña con un glifo de estado (`✳` reposo, `◐◓◑◒` trabajando) +
  tema de la sesión. `title_regex` por defecto: `^[✳✻✽✶✢·◐◓◑◒]\s|Claude Code`.
- `require_process` (por defecto `true`): la ventana solo cuenta si su proceso
  (`WindowsTerminal.exe`) tiene un `claude.exe` vivo entre sus descendientes
  (`claude.exe → shell → WindowsTerminal.exe`). Evita pegar en pestañas cuyo Claude terminó.
  Limitación: WT aloja varias ventanas/pestañas en un mismo proceso, así que no distingue
  entre pestañas de ese proceso.
- **WSL** (`wsl = true`): desde Windows no se ve el `claude` de WSL, solo `wsl.exe`. Para los
  `wsl.exe` bajo una ventana de WT se lee la distro de su línea de órdenes (`-d X`) y se
  ejecuta `wsl.exe -d X -e sh -c "pgrep -x claude || pgrep -f '[c]laude-code'"` (`_wsl.py`).
  Si no se puede comprobar (timeout 3 s), se acepta. Solo se consulta una distro que ya
  está en marcha (hay un `wsl.exe` abierto), así que no arranca la VM.

## browser
- Ventanas `Chrome_WidgetWin_1` cuyo proceso está en `browsers` (Chrome, Edge, Brave,
  Vivaldi, Opera). Firefox no está probado.
- **Puntuación 0 (URL):** solo la pestaña visible de cada ventana expone su URL, en la barra
  de direcciones (`EditControl` de clase `OmniboxViewViews`). `url_regex` = `claude.ai`.
  Es la única forma de reconocer proyectos de **Claude Design**, que se titulan con el
  nombre del proyecto.
- **Puntuación 1 (título):** pestañas de fondo. Chrome/Edge decoran el nombre accesible
  (`Uso de memoria de X: 345 MB`, `X: parte del grupo Y`, `X - Uso de memoria - 20 MB`), así
  que la regex busca la palabra `Claude` suelta seguida de fin, `:`, `(` o ` - `.
- `_before_paste`: UIA solo ve el DOM de la pestaña activa → tras seleccionarla, busca un
  `EditControl` con la clase CSS **exacta** `ProseMirror` (el prompt de Chat, Code y Design;
  no depende del idioma) y le da el foco. Ojo: hay contenedores con clases tipo
  `[&_.ProseMirror]:...`, por eso se compara por token. Chrome tiene varios
  `DocumentControl` (paneles internos): no buscar en el primero, recorrer la ventana.
- Títulos reales observados: `Nuevo chat - Claude`, `<conversación> - Claude`,
  `Claude Code`, `Design - Claude` (galería), `<proyecto>` (proyecto de Design).
- Mejora futura: una extensión de navegador daría la URL de todas las pestañas.
- **Solo chats (`chat_url_regex`, lista blanca en `browser.py`):** no todo claude.ai tiene
  prompt. Los artifacts (`/artifact/<id>`, `/code/artifact/<uuid>`: los documentos tienen un
  editor `ProseMirror`, así que el pegado "funciona" sin llegar a un chat), `/recents`,
  `/projects`, `/settings`, `/share/...` se descartan. Una pestaña de claude.ai que no case
  se ignora aunque su título case. En `browser` las de fondo se eligen por título, así que la
  URL se comprueba otra vez en `_before_paste`, ya visible. Lo aplican también
  `browser_extension` (en `locate`, sobre la URL de cada pestaña) y `macos_browser`;
  `linux_browser` solo ve el título y no puede.

Depurar siempre con `python -m paste_photo --probe` (no pega nada).
