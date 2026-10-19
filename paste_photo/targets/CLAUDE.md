# targets/ — dónde está Claude Code y cómo pegar

Recuerda la regla obligatoria del CLAUDE.md raíz: todo cambio lleva entrada en `CHANGELOG.md`.

Strategy + Registry: cada destino es un módulo que registra un *builder*
`(options: Mapping, ctx: TargetContext) -> TargetStrategy` con `@register_target("tipo")`.
`options` es la tabla `[[targets]]` de `config.toml`; `ctx` trae `platform`, `focus` y `keyboard`.

| Tipo | Estado | Pegado |
|---|---|---|
| `windows_terminal` | ✅ | `alt+v` (Ctrl+V en WT solo pega texto) |
| `desktop_app` | ⏳ `_pending` | Ctrl+V / Cmd+V |
| `browser` (claude.ai/code) | ⏳ `_pending` | Ctrl+V / Cmd+V |
| `vscode` | ⏳ `_pending` | Ctrl+V / Cmd+V |

## Receta: añadir un destino
1. Crea `targets/<tipo>.py` con una clase que cumpla `TargetStrategy` (`name`, `locate`, `paste`).
2. Registra un builder con `@register_target("<tipo>")`; valida `ctx.platform` y lee
   opciones con valores por defecto.
3. Importa librerías de SO **dentro del constructor** (el módulo se importa en todos los SO).
4. Añade el módulo a `_BUILTIN_MODULES` en `registry.py` (o sustituye su stub `_pending`).
5. Documenta sus opciones en `config.toml` (comentadas) y en el README.
6. Tests en `tests/` con `FakeFocus`/`FakeKeyboard` para la lógica que no toque el SO.
7. CHANGELOG: `Added`.

## Reglas para `locate()` y `paste()`
- `locate()` sin efectos visibles: no enfocar, no cambiar de pestaña.
- `paste()` usa `ctx.focus.activate()` y `ctx.keyboard.send_hotkey()`; nunca envía Enter.
- Si el destino cambia estado interno (pestaña), restáuralo al final; el foco de ventana
  lo restaura el Orchestrator.

## windows_terminal
- Ventanas de clase `CASCADIA_HOSTING_WINDOW_CLASS`; pestañas = `TabItemControl` por UI Automation.
- Claude Code titula la pestaña con un glifo de estado (`✳` reposo, `◐◓◑◒` trabajando) +
  tema de la sesión. `title_regex` por defecto: `^[✳✻✽✶✢·◐◓◑◒]\s|Claude Code`.
- Si hay varias coincidencias: seleccionada > en la ventana activa > primera.
- Depurar con `python -m paste_photo --probe`.
