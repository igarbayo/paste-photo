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
| `browser_extension` | Windows, Linux | la extensión inyecta un `paste` con el PNG en el editor | no |
| `windows_terminal` | Windows | UI Automation: selecciona la pestaña, **Alt+V** | sí |
| `browser` | Windows | UI Automation: pestaña + editor (solo enfoca si no lo tenía), Ctrl+V | sí |
| `orca` | Windows, Linux | `orca terminal send --terminal $ORCA_TERMINAL_HANDLE --text <tecla>` | no |
| `tmux` | Linux, macOS | `tmux -S <socket> send-keys -t <pane> C-v` | no |
| `kitty` | Linux, macOS | `kitty @ --to $KITTY_LISTEN_ON send-text --match id:N ` | no |
| `wezterm` | Linux, macOS | `wezterm cli send-text --no-paste --pane-id N ` | no |
| `konsole` | Linux | D-Bus `org.kde.konsole.Session.sendText("")` | no |
| `linux_terminal` | Linux | `WindowSystem.activate` + **Ctrl+V** (solo si la pestaña de Claude es la activa) | sí |
| `desktop_app`, `vscode` | — | ⏳ `_pending` | |

Estado real: probados de punta a punta en Linux (WSL + Xvfb/Openbox) tmux, kitty, Konsole,
`linux_terminal` (xterm), `orca` (.deb) y `browser_extension` (Chromium); `orca` también en
Windows; WezTerm solo con tests unitarios.

## Posición del cursor: la imagen va donde estaba el cursor
- **Terminales**: se envía solo la tecla de pegado; Claude Code inserta `[Image #N]` en su
  cursor. Nunca escribir texto ni mover el cursor (flechas, Fin...).
- **`browser_extension`**: `cursor.js` (content script, mismo mundo aislado que
  `pasteImage`) guarda la última selección dentro del prompt. `pasteImage` usa la actual si
  está en el prompt, si no esa última, si no el final; espera 50 ms antes del `paste` para que
  ProseMirror lea la selección (`selectionchange` es asíncrono).
- **`browser` (UIA)**: si el editor ya tiene el foco no se toca; si no, `SetFocus()` y
  ProseMirror restaura su última selección (~20 ms). Un `Ctrl+End` la pisaría. Sin
  extensión no se distingue "nunca tuvo cursor" (va al principio).
- Pruebas: página con ProseMirror real (`esm.sh`, `role="textbox"` para que UIA lo vea como
  `EditControl`); en Chromium con `--load-extension`, **perfil nuevo** en cada prueba: el
  service worker de la extensión queda en caché aunque cambie el archivo.

## Destinos de terminal en Linux: el entorno del proceso manda
`_processes.claude_processes()` encuentra los `claude` (nombre o `@anthropic-ai/claude-code`
en la línea de órdenes) y lee su **entorno**, que delata el panel exacto: `TMUX`+`TMUX_PANE`,
`KITTY_WINDOW_ID`+`KITTY_LISTEN_ON`, `WEZTERM_PANE`, `KONSOLE_DBUS_SERVICE`+`KONSOLE_DBUS_SESSION`.
- Base común `_env_terminal.EnvTerminalTarget`: cada terminal solo define `describe()` y
  `send_ctrl_v()`.
- **tmux manda**: si `TMUX` está, los terminales exteriores (kitty, WezTerm, Konsole) ignoran
  ese proceso; si no, su Ctrl+V iría al panel activo de tmux, no al de Claude.
- `linux_terminal` solo atiende procesos que **no** cubre ningún IPC (`handled_by_ipc`).
- La ventana de un proceso = primera ventana cuyo PID es un ancestro (`owning_window`);
  un destino puede cambiarlo con `window_of()` (Orca: sus PTY cuelgan del daemon).

## Orca (`orca.py`, Windows y Linux)
- Orca exporta `ORCA_TERMINAL_HANDLE` (y `ORCA_CLI_COMMAND`) a sus terminales; está en
  `IPC_ENV_MARKERS`, así que `linux_terminal` no lo duplica.
- CLI: `orca.exe` (Windows, `%LOCALAPPDATA%\Programs\orca\resources\bin`; no `orca.cmd`,
  cmd.exe reinterpreta el texto) y `orca-ide` en Linux (`orca` es el lector de pantalla de
  GNOME). Opción `cli` para fijarla.
- Bytes: `\x1bv` (Alt+V) en Windows, `\x16` en Linux (`paste_text`). Sin `--enter`.
- Recencia: cualquier ventana del proceso `orca.exe`/`orca-ide` (la usada más recientemente).

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

Depurar siempre con `python -m paste_photo --probe` (no pega nada).
