# ui/: interfaces de usuario

Recuerda la regla obligatoria del CLAUDE.md raíz: todo cambio lleva entrada en `CHANGELOG.md`.

Todas las interfaces usan **`PasteService`** (`paste_photo/service.py`) y nunca tocan los
adaptadores del SO directamente.

| Interfaz | Archivo | Cómo se abre |
|---|---|---|
| Bandeja del sistema | `tray.py` (pystray) | `paste-photo` / `paste-photo.exe` (por defecto) |
| Consola | `console.py` | `paste-photo run` / `paste-photo-cli.exe run` |

## Contrato de `PasteService`
- `start()` / `stop()`: arranca y para el hilo de trabajo y la fuente de capturas.
  `start()` relanza cualquier error de arranque (destino desconocido, etc.).
- `pause()` / `resume()` / `active`: las capturas en pausa se ignoran.
- `subscribe(listener)`: recibe `Pasted`, `NotPasted` y `StateChanged`
  (`core/events.py`). **Se llama desde el hilo de trabajo**: no bloquees ni toques UI que
  exija su propio hilo sin delegar.
- `submit(fn)` → `Future`: ejecuta `fn(orquestador)` en el hilo de trabajo. Todo lo que
  toque UI Automation/COM, el foco o el teclado va por aquí (`probe()` y `set_prefer()` son
  atajos).

## Receta: añadir una opción al menú de la bandeja
1. Añade un `pystray.MenuItem` en `TrayApp._menu()` (texto, acción y, si es interruptor,
   `checked=lambda _: ...`).
2. La acción es un método de `TrayApp`. Si necesita el SO, usa `self._service.submit(...)`;
   si es un ajuste persistente, actualiza el estado en memoria y llama a
   `self._save_setting(clave, valor)` (escribe en `[general]` conservando comentarios).
3. Si el ajuste es nuevo: añádelo con comentario a `resources/default_config.toml`, a
   `Config` y a `parse_config()` en `config.py`, y a la tabla del README si es visible.
4. Tests: la lógica va en el servicio o en el orquestador (con fakes), no en la bandeja.
5. Verifica a mano: abre el menú (clic derecho; en Windows 11 los iconos nuevos van al
   desbordamiento `^`).

## Receta: añadir otra interfaz (p. ej. una ventana)
Crea `ui/<nombre>.py` que reciba un `PasteService`, se suscriba a sus eventos y llame a sus
métodos; añade el modo en `MODES` y `_dispatch()` de `__main__.py`.

## Detalles de la bandeja
- `pystray.Icon.run(setup=...)`: `setup` corre en otro hilo; ahí se arranca el servicio.
- Icono en pausa = icono normal en gris (`_icon_images`).
- Notificaciones: `icon.notify()`. Respetan `notify` salvo las que pide el usuario
  (`force=True`, p. ej. "¿Dónde pegaría ahora?").
- "Iniciar con Windows" usa el puerto `Autostart` de la plataforma con
  `app.launch_command()` (el `.exe` si está empaquetado; `pythonw -m paste_photo` si no).
