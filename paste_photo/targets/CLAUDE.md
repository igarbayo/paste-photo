# targets/ — dónde está Claude y cómo pegar

Recuerda la regla obligatoria del CLAUDE.md raíz: todo cambio lleva entrada en `CHANGELOG.md`.

Strategy + Registry: cada destino es un módulo que registra un *builder*
`(options: Mapping, ctx: TargetContext) -> TargetStrategy` con `@register_target("tipo")`.
`options` es la tabla `[[targets]]` de `config.toml`; `ctx` trae `platform`, `focus` y `keyboard`.

| Tipo | Estado | Pegado |
|---|---|---|
| `windows_terminal` | ✅ Windows | `alt+v` (Ctrl+V en WT solo pega texto) |
| `browser` (claude.ai: Chat, Code, Design) | ✅ Windows · Chrome, Edge, Chromium | `ctrl+v` |
| `desktop_app` | ⏳ `_pending` | Ctrl+V / Cmd+V |
| `vscode` | ⏳ `_pending` | Ctrl+V / Cmd+V |

## Receta: añadir un destino
1. Crea `targets/<tipo>.py` con una clase que cumpla `TargetStrategy` (`name`, `locate`, `paste`).
   - Si en Windows se basa en **pestañas visibles por UI Automation**, hereda de
     `_win_uia.UiaTabTarget` e implementa solo lo que cambia (ver abajo).
2. Registra un builder con `@register_target("<tipo>")`; valida `ctx.platform` y lee
   opciones con valores por defecto.
3. Importa librerías de SO **dentro del constructor o de una función** (el módulo se importa
   en todos los SO). Patrón en `browser.py`: `_windows_browser_target()` define la clase.
4. Añade el módulo a `_BUILTIN_MODULES` en `registry.py` (o sustituye su stub `_pending`).
5. Documenta sus opciones en `config.toml` (comentadas) y en el README.
6. Tests en `tests/`: lógica pura (regex, puntuación) con nombres **reales** observados.
7. CHANGELOG: `Added`.

## `UiaTabTarget` (Template Method, `_win_uia.py`)
Puntos de extensión:
- `_candidate_windows()` → hwnds a inspeccionar (obligatorio).
- `_rank(hwnd, tab, selected)` → `None` si no es Claude; menor = mejor (por defecto: `title_regex`).
- `_before_paste(handle)` → con la pestaña ya visible; lanza `TabNotReady` para descartarla
  y que se pruebe la siguiente candidata.

Lo común: ordena candidatos (puntuación > visible > ventana activa > orden), los prueba en
orden, pega con `paste_keys` y **restaura la pestaña seleccionada** de cada ventana tocada.
Lee propiedades UIA con `safe_attr()` y recorre con `_walk()`: los elementos desaparecen a
mitad de recorrido (COMError) cuando la página cambia.

## Reglas para `locate()` y `paste()`
- `locate()` sin efectos visibles: no enfocar, no cambiar de pestaña.
- `paste()` usa `ctx.focus.activate()` y `ctx.keyboard.send_hotkey()`; **nunca envía Enter**.
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
