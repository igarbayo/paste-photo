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
| `TargetStrategy` | `locate()` es rápido y sin efectos visibles (devuelve `TargetHandle` o `None`; `extra["last_used"]` opcional en segundos epoch); `paste(handle, shot)` pega **sin Enter** y puede restaurar su estado interno (p. ej. pestaña) |
| `WindowSystem` | `list_windows()` → `WindowInfo(id, title, pid, app_id)`; `active_window()`; `activate(id)`. Lo usan `linux_terminal`, el foco en Linux y la prioridad reciente |

## Orchestrator
- `prefer = "recent"` (por defecto): pregunta a **todos** los destinos y gana el Claude cuya
  ventana usó el usuario por última vez (`recency.Recency`, alimentado por `app.py` con la
  ventana activa cada 0,25 s); el orden de `config.toml` solo desempata.
  `prefer = "order"`: gana el primer destino de la config (Chain of Responsibility).
- `candidates()` devuelve el orden sin pegar (lo usa `--probe`).
- Cada imagen se pega **una sola vez**: recuerda los últimos `remember_images` hashes (LRU).
  No usar ventanas de tiempo: otras apps devuelven la misma imagen al portapapeles minutos
  después (gestores de portapapeles, dictado tipo Wispr Flow) y se repegaría.
- Una excepción en `locate()` o en `paste()` se registra y se pasa al siguiente destino.
- `restore_focus` envuelve `paste()` con `preserve_focus` (Memento).

Si cambias un contrato: actualiza esta tabla, los fakes, los adaptadores y el CHANGELOG
(`Changed`, y es cambio rompedor si afecta a adaptadores de terceros).
