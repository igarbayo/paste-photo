# core/ — dominio puro

Recuerda la regla obligatoria del CLAUDE.md raíz: todo cambio lleva entrada en `CHANGELOG.md`.

## Invariantes
- Solo biblioteca estándar. Prohibido importar `win32*`, `uiautomation`, `pyobjc`,
  `platforms/` o `targets/`.
- Todo lo de aquí se testea con `tests/fakes.py` en cualquier SO.
- Los puertos son `Protocol`: los adaptadores no heredan, solo cumplen la forma.

## Contratos (`ports.py`)
| Puerto | Contrato |
|---|---|
| `ScreenshotSource` | `start(on_capture)` no bloquea (hilo propio); `on_capture` puede llamarse desde otro hilo; `stop()` es idempotente y libera recursos del SO |
| `Keyboard` | `send_hotkey("alt+v")` envía la combinación a la ventana con foco. Formato parseado por `hotkey.parse_hotkey` |
| `FocusManager` | `capture()` devuelve un snapshot opaco; `restore(snapshot)` tolera ventanas ya cerradas; `activate(id)` trae la ventana al frente |
| `TargetStrategy` | `locate()` es rápido y sin efectos visibles (devuelve `TargetHandle` o `None`); `paste(handle)` enfoca, pega **sin Enter** y puede restaurar su estado interno (p. ej. pestaña) |

## Orchestrator
- Chain of Responsibility: destinos en el orden de `config.toml`; gana el primero.
- Deduplica por `image_hash` dentro de `debounce_s`.
- Una excepción en `locate()` pasa al siguiente destino; en `paste()` se registra y se aborta.
- `restore_focus` envuelve `paste()` con `preserve_focus` (Memento).

Si cambias un contrato: actualiza esta tabla, los fakes, los adaptadores y el CHANGELOG
(`Changed`, y es cambio rompedor si afecta a adaptadores de terceros).
