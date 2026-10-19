# paste-photo

Haz una captura y aparece sola en Claude.

`paste-photo` vigila tus capturas de pantalla y, si tienes Claude abierto (Claude Code en la
terminal o cualquier chat de claude.ai en el navegador), enfoca su pestaña, pega la imagen
(sin enviarla) y te devuelve a la ventana y pestaña en las que estabas.

## Soporte

| Sistema | Destino | Estado |
|---|---|---|
| Windows 10/11 | Claude Code en **Windows Terminal** | ✅ |
| Windows 10/11 | **Navegador**: cualquier chat de claude.ai (Chat, Code, Design) en Chrome, Edge y demás Chromium | ✅ |
| Windows | Firefox | ⏳ sin probar |
| Windows/macOS/Linux | App oficial de escritorio | ⏳ pendiente |
| Windows/macOS/Linux | Extensión de VS Code | ⏳ pendiente |
| macOS, Linux | Cualquiera | ⏳ pendiente |

La arquitectura ya está preparada para todos ellos; ver [ADR 0001](docs/adr/0001-arquitectura-hexagonal.md).

## Requisitos
- Python 3.11 o superior
- Claude Code en una pestaña de Windows Terminal, o claude.ai abierto en Chrome/Edge

## Instalación
```bash
pipx install .                      # instalación global con el comando `paste-photo`
# o, para desarrollo:
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
```

## Uso
```bash
paste-photo                 # se queda escuchando; Ctrl+C para salir
paste-photo --probe         # dice en qué pestaña pegaría, sin pegar nada
paste-photo --debug         # logs detallados
paste-photo --config RUTA   # usar otro config.toml
paste-photo --list-targets  # tipos de destino disponibles
```

1. Abre Claude Code en Windows Terminal, o claude.ai (Chat, Code o Design) en el navegador.
2. Lanza `paste-photo`.
3. Pulsa **Win+Shift+S** y recorta. La imagen queda adjunta en el prompt de Claude
   (`[Image #N]` en la terminal); escribe tu mensaje y envíalo cuando quieras.

Si hay varios sitios con Claude, se usa el orden de `[[targets]]` en `config.toml`
(por defecto: terminal y luego navegador) y, dentro de cada uno, la pestaña más visible.

## Configuración
Se busca `config.toml` en: `--config RUTA` → directorio actual →
`%APPDATA%\paste-photo\config.toml`. Si no hay ninguno, se usan los valores por defecto.

| Clave | Por defecto | Para qué |
|---|---|---|
| `general.debounce_ms` | `2000` | Ignora la misma imagen repetida en ese intervalo |
| `general.restore_focus` | `true` | Volver a tu ventana tras pegar |
| `targets[].type` | `windows_terminal`, `browser` | Tipo de destino (en orden de prioridad) |
| `targets[].enabled` | `true` | Desactivar un destino sin borrarlo |
| `title_regex` | según destino | Qué pestaña es Claude (por su título) |
| `paste_keys` | `alt+v` (terminal), `ctrl+v` (navegador) | Combinación de pegado |
| `settle_ms` | `150` / `250` | Espera tras enfocar antes de pulsar teclas |
| `restore_tab` | `true` | Volver a la pestaña que tenías seleccionada |
| `require_process` (terminal) | `true` | Exigir un `claude.exe` vivo en esa ventana de WT |
| `browsers` (navegador) | Chrome, Edge, Brave, Vivaldi, Opera | Procesos de navegador a mirar |
| `url_regex` (navegador) | `claude.ai` | URL que identifica la pestaña visible |
| `editor_class` (navegador) | `ProseMirror` | Solo se pega si existe el prompt |

**¿Solo una pestaña concreta?** Pon en `title_regex` parte de su título, p. ej. `"mi-proyecto"`.
Comprueba el resultado con `paste-photo --probe`.

Ejemplo completo y comentado: [config.toml](config.toml).

## Arrancar con Windows
Crea un acceso directo en `shell:startup` (Win+R → `shell:startup`) que ejecute
`pythonw -m paste_photo` (o `paste-photo` si lo instalaste con pipx).

## Limitaciones
- Cualquier imagen copiada al portapapeles (no solo capturas) se pega.
- Terminal: la detección se basa en el título de la pestaña que pone Claude Code; si
  cambia, ajusta `title_regex`.
- Navegador: solo se conoce la URL de la pestaña **visible** de cada ventana. Las de
  segundo plano se reconocen por título, así que un proyecto de Claude Design (titulado
  con su nombre) solo se detecta si está visible.
- Durante un instante se enfoca la ventana/pestaña de Claude.
- Si lo lanzas desde una sesión de Claude Code, esa sesión será el destino.

## Desarrollo
```bash
.venv\Scripts\python -m pytest -q
.venv\Scripts\ruff check .
```
- Guía para agentes de IA: [CLAUDE.md](CLAUDE.md) (+ `CLAUDE.md` en `core/`, `platforms/`, `targets/`).
- Todo cambio se anota en [CHANGELOG.md](CHANGELOG.md) (formato Keep a Changelog).
