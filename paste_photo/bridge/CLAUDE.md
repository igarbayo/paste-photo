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
| `install.py` | `setup browser`: copia la extensión a una carpeta estable, genera la de Firefox (`firefox_manifest`, carpeta + `.xpi`) y registra el host. Chromium: `~/.config/<navegador>/NativeMessagingHosts` / `HKCU\Software\<navegador>\NativeMessagingHosts`, con `allowed_origins`. Firefox y LibreWolf: `~/.mozilla` / `~/.librewolf` + `native-messaging-hosts` / `HKCU\Software\Mozilla` y `\LibreWolf` + `\NativeMessagingHosts`, con `allowed_extensions` (en Windows, archivo `<host>.firefox.json` aparte) |
| `../resources/extension/` | `background.js`: `list` / `paste` / `ping`; reconecta con espera creciente y alarma de 1 min (el service worker de MV3 duerme; en Firefox es una página de fondo) |
| `../resources/extension/cursor.js` | Content script: guarda la última selección dentro del prompt |

## Mensajes (todos con `id`; la respuesta repite el `id`)
- `{"cmd": "list"}` → `{"ok", "tabs": [{tabId, windowId, url, title, active, lastUsed}]}`.
  `lastUsed` (ms epoch) = ahora si es la pestaña activa de la ventana con foco; si no, cuándo
  **dejó** de estar en uso (`onActivated` / `onFocusChanged`).
- `{"cmd": "paste", tabId, png (base64), name, activate}` → `{"ok"}` o
  `{"ok": false, "error": "no-editor" | "paste-ignored" | ...}`. Dos `executeScript`:
  `placeCaret` (mundo aislado, donde `cursor.js` guarda la última posición) coloca la
  selección y `dispatchPaste` (`world: "MAIN"`) lanza un `ClipboardEvent("paste")` con
  `DataTransfer` + `File` sobre `.ProseMirror` (verificado en claude.ai Chat, Code y Design).
  En Firefox, un evento creado en el mundo aislado llega a la página **sin archivos**, y
  `new ClipboardEvent(..., {clipboardData})` crea uno vacío: por eso el mundo de la página y,
  si hace falta, `clipboardData` con `defineProperty`. No necesita foco: funciona en
  pestañas de fondo.
- Extensión → host: `{"event": "hello", version}` al conectar.
- Host → extensión: un mensaje > 1 MB se manda como `{"chunk", "seq", "total", "data"}`.

## ID fijo de la extensión
`manifest.json` lleva `"key"` (clave pública RSA); el ID (`protocol.EXTENSION_ID`) se deriva
de ella y es el `allowed_origins` del host. `tests/test_linux.py` comprueba que coinciden. La
clave privada **no** se guarda (no hace falta para "cargar descomprimida"). Si algún día se
publica en Chrome Web Store, la tienda asigna otro ID: añadirlo a `allowed_origins`.

## Firefox
- Una sola fuente: `resources/extension/` es la de Chromium; `install.firefox_manifest()`
  quita `key`, cambia `background.service_worker` por `background.scripts` y añade
  `browser_specific_settings.gecko` (ID `protocol.FIREFOX_EXTENSION_ID`, mínimo 128.0,
  `data_collection_permissions: none`, que AMO exige). `packaging/firefox_xpi.py` la empaqueta
  para la release.
- Firefox normal solo instala `.xpi` **firmados** por Mozilla (la release los firma con
  `web-ext sign --channel=unlisted` si hay secretos `AMO_JWT_*`). ESR, Developer Edition,
  Nightly y LibreWolf admiten sin firmar con `xpinstall.signatures.required = false`.
- Firefox pasa al host otros argumentos (ruta del manifiesto, ID): `native_host.py` los ignora.
- La página de fondo de Firefox se descarga al rato; la reconexión (alarma) basta: probado con
  75 s sin actividad antes de pegar.
- GNOME Web (Epiphany) **no** sirve: su API de extensiones no tiene `connectNative` ni
  `scripting` (ver `src/webextension/api/runtime.c`); se usa `linux_browser`.

## Probar
- Unitario + relevo real con procesos: `tests/test_bridge.py` (aislado con
  `PASTE_PHOTO_BRIDGE_ADDRESS` y `PASTE_PHOTO_STATE_DIR`).
- Navegador real: ver "Verificación manual → Linux" en el CLAUDE.md raíz (Chromium con
  `--load-extension`, copia de la extensión apuntando a una página local).
- Chrome de marca ≥ 137 ya no acepta `--load-extension`: cargar a mano como descomprimida.
- Firefox: perfil nuevo con `user.js` (`xpinstall.signatures.required=false`,
  `extensions.autoDisableScopes=0`) y el `.xpi` en `<perfil>/extensions/<ID>.xpi`; Firefox ESR
  (Debian `firefox-esr`; en Windows, portable con `setup.exe /ExtractDir=<carpeta>`).
- Chromium: **perfil nuevo** en cada prueba; el service worker de la extensión queda en caché.
- Chromium en **snap** limita el native messaging (`doctor` lo menciona en el README).
