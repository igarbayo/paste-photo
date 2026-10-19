# bridge/: extensión del navegador ⇄ paste-photo

Recuerda la regla obligatoria del CLAUDE.md raíz: todo cambio lleva entrada en `CHANGELOG.md`.

```
extensión (resources/extension, MV3) ⇄ native messaging (stdin/stdout, 4 bytes + JSON)
    ⇄ paste-photo-native-host (native_host.py, lo lanza el navegador)
    ⇄ canal local autenticado (multiprocessing.connection: Unix socket / named pipe)
    ⇄ BridgeServer (server.py, en el servicio) ⇄ destino browser_extension
```

## Piezas
| Archivo | Qué hace |
|---|---|
| `protocol.py` | Nombre del host, **ID de la extensión**, dirección del canal, `authkey` (archivo 0600 en el estado del usuario), framing y **troceo** de mensajes > 1 MB |
| `server.py` | `BridgeServer.instance()`: escucha; un `BrowserClient` por navegador con `request()` (id + futuro). Responde `status` (para `doctor`) |
| `native_host.py` | Relevo bidireccional; si el servicio no está abierto, reintenta cada 2 s. Al reconectar reenvía el `hello` |
| `install.py` | `setup browser`: copia la extensión a una carpeta estable y registra el host (Linux: `~/.config/<navegador>/NativeMessagingHosts`; Windows: `HKCU\Software\<navegador>\NativeMessagingHosts`) |
| `../resources/extension/` | `background.js`: `list` / `paste` / `ping`; reconecta con espera creciente y alarma de 1 min (el service worker de MV3 duerme) |

## Mensajes (todos con `id`; la respuesta repite el `id`)
- `{"cmd": "list"}` → `{"ok", "tabs": [{tabId, windowId, url, title, active, lastUsed}]}`.
  `lastUsed` (ms epoch) = ahora si es la pestaña activa de la ventana con foco; si no, cuándo
  **dejó** de estar en uso (`onActivated` / `onFocusChanged`).
- `{"cmd": "paste", tabId, png (base64), name, activate}` → `{"ok"}` o
  `{"ok": false, "error": "no-editor" | "paste-ignored" | ...}`. Inyecta en la página un
  `ClipboardEvent("paste")` con `DataTransfer` + `File` sobre `.ProseMirror` (verificado en
  claude.ai Chat, Code y Design). No necesita foco: funciona en pestañas de fondo.
- Extensión → host: `{"event": "hello", version}` al conectar.
- Host → extensión: un mensaje > 1 MB se manda como `{"chunk", "seq", "total", "data"}`.

## ID fijo de la extensión
`manifest.json` lleva `"key"` (clave pública RSA); el ID (`protocol.EXTENSION_ID`) se deriva
de ella y es el `allowed_origins` del host. `tests/test_linux.py` comprueba que coinciden. La
clave privada **no** se guarda (no hace falta para "cargar descomprimida"). Si algún día se
publica en Chrome Web Store, la tienda asigna otro ID: añadirlo a `allowed_origins`.

## Probar
- Unitario + relevo real con procesos: `tests/test_bridge.py` (aislado con
  `PASTE_PHOTO_BRIDGE_ADDRESS` y `PASTE_PHOTO_STATE_DIR`).
- Navegador real: ver "Verificación manual → Linux" en el CLAUDE.md raíz (Chromium con
  `--load-extension`, copia de la extensión apuntando a una página local).
- Chrome de marca ≥ 137 ya no acepta `--load-extension`: cargar a mano como descomprimida.
- Chromium en **snap** limita el native messaging (`doctor` lo menciona en el README).
