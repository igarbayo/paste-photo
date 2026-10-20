# CLAUDE.md — PastePhoto

Pega automáticamente cada captura de pantalla en el Claude que estés usando: Claude Code en
cualquier terminal (Windows Terminal, también con WSL; en Linux tmux, kitty, WezTerm, Konsole
o cualquier otro) o cualquier chat de claude.ai en navegadores Chromium y Firefox (y Safari en macOS).
Corre en la bandeja del sistema en **Windows, macOS** (iTerm2, Terminal, tmux...)
**y Linux** (X11, GNOME Wayland, KDE Wayland). Diseñado para crecer (app de escritorio,
VS Code) **sin tocar el núcleo**.

## ⚠️ Regla obligatoria: CHANGELOG
**Todo cambio** (código, config, docs, dependencias) se acompaña de una entrada en
`CHANGELOG.md` bajo `## [Unreleased]`, en la categoría de [Keep a Changelog 1.1.0](https://keepachangelog.com/es-ES/1.1.0/):
`Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`.
Una tarea **no está terminada** sin su entrada. Al publicar versión: ver
`packaging/CLAUDE.md` → "Publicar una versión".

## ⚠️ Regla obligatoria: README siempre al día
`README.md` describe **exactamente lo que el producto hace hoy**: funcionalidades
desarrolladas, plataformas soportadas, instalación, uso, configuración y problemas
frecuentes. Cada vez que se añade, cambia o quita una funcionalidad visible para el usuario,
se actualiza el README **en el mismo cambio** (nada de funciones sin documentar ni de
promesas de cosas que aún no existen). Lo no probado en real se marca "Experimental".
Una tarea **no está terminada** sin ello. El README está en inglés (ver Convenciones).

## ⚠️ Regla obligatoria: metadatos públicos al día
Igual que el README: cuando cambia lo que el producto hace (plataformas, terminales,
navegadores, forma de distribuirse), se revisan **en el mismo cambio** todas las
descripciones públicas, en inglés y con los mismos hechos que el README:
- **About de GitHub** (descripción, máx. 350 caracteres, y *topics*):
  `gh repo edit igarbayo/paste-photo --description "..." --add-topic a,b` /
  `--remove-topic x`; comprobar con `gh repo view --json description,repositoryTopics`.
- `pyproject.toml`: `description`, `keywords`, `classifiers`.
- winget: `ShortDescription`, `Description` y `Tags` en `packaging/winget/make_manifests.py`
  (se publican con la siguiente versión).
- `.deb`: `Description` y `.desktop` (`Comment`) en `packaging/linux/build_deb.py`.
- Extensión: `description` de `resources/extension/manifest.json`.
- `CONTRIBUTING.md` (requisitos para probar).
- Imagen social y logo (`docs/assets/`, textos en `packaging/make_brand.py`): si cambian las
  etiquetas (plataformas, navegadores), regenerar con `python packaging/make_brand.py` y
  volver a subir `social-preview.png` en GitHub → Settings → General → Social preview
  (no hay API: a mano o con el navegador).
- Demo animada (`docs/assets/demo.gif`): si cambia lo que se ve al pegar (bandeja, mensajes,
  flujo en la terminal), volver a grabarla con `packaging/demo/demo.py`.
Una tarea **no está terminada** sin ello. Lo que no está en un archivo del repo (About,
topics) se cambia con `gh` y se anota en el CHANGELOG.

## ⚠️ Regla obligatoria: licencias
El proyecto es **MIT** (`LICENSE`, `LICENSES/MIT.txt`). Archivo `.py`/`.js` nuevo → cabecera
`SPDX-FileCopyrightText: 2026 igarbayo` + `SPDX-License-Identifier: MIT`.
Dependencia nueva → comprobar su licencia **antes** de añadirla (GPL/AGPL: no sin consultar,
cambiaría la licencia del instalador; LGPL: `module_collection_mode` del spec en Windows y,
en Linux, mejor paquete de Debian en `DEPENDS`) y actualizar `docs/COMPONENTS_LICENSE.md`.
Los avisos de terceros del instalador los genera `packaging/third_party.py`.

## Git
- Repositorio **público** `igarbayo/paste-photo`; se trabaja directamente sobre `main`.
- Tras **cada** cambio: commit + `git push origin main`.
- Commits **sin firma GPG** (`git -c commit.gpgsign=false commit ...`) y **sin** líneas
  `Co-Authored-By`.
- Mensajes en formato Conventional Commits (`feat:`, `fix:`, `docs:`...).

## Mapa
```
paste_photo/
  core/          dominio puro: eventos, puertos (Protocols), Orchestrator   → core/CLAUDE.md
  platforms/     Abstract Factory por SO: capturas, ventanas, foco, teclado,
                 autoarranque (windows/, macos/, linux/ por sesión)          → platforms/CLAUDE.md
  targets/       Strategy + Registry: dónde está Claude y cómo pegar         → targets/CLAUDE.md
  bridge/        puente con la extensión del navegador (native messaging)    → bridge/CLAUDE.md
  ui/            interfaces: bandeja (por defecto) y consola                 → ui/CLAUDE.md
  service.py     PasteService: motor en segundo plano que usan todas las interfaces
  app.py         instancia única, --probe, logs, orden de autoarranque
  doctor.py      `paste-photo doctor`: diagnóstico con soluciones
  config.py      config.toml → Config; guardar ajustes (tomlkit)
  paths.py       rutas de usuario por SO (config, logs, datos, estado)
  imaging.py     conversión a PNG (DIB de Windows, formatos de Linux, TIFF de macOS)
  resources/     default_config.toml, iconos, extension/ (Chromium), gnome_extension/
  __main__.py    CLI: [tray|run|doctor|setup browser|gnome] --probe --list-targets
packaging/       build.py, PyInstaller, Inno Setup, winget, linux/build_deb.py → packaging/CLAUDE.md
.github/workflows/  ci.yml (tests Win/macOS/Linux, integración X11 y macOS, .exe, .deb) y
                 release.yml
tests/           pytest con fakes; tests/integration: Linux/X11 y macOS reales
                 (PASTE_PHOTO_INTEGRATION=1)
docs/adr/        decisiones de arquitectura
```

Flujo: `ScreenshotSource` (hilo propio) → cola → hilo de trabajo de `PasteService` →
`Orchestrator.handle()` → `locate()` de los destinos de este SO → se ordenan por último uso
(`last_used` del destino o ventana usada más recientemente, `Recency`) → `paste(handle, shot)`
dentro de `preserve_focus()`; si falla, el siguiente → evento `Pasted`/`NotPasted`.
Una sola instancia a la vez (bloqueo en el directorio temporal).

⚠️ Al probar en real: **para siempre** las instancias que lances en segundo plano
(`Get-Process paste-photo*` y `Get-CimInstance Win32_Process ... *paste_photo*`; en Linux
`pkill -f paste_photo`). Una instancia olvidada con una config de prueba siguió pegando en
Chrome en lugar de en la terminal del usuario.

## Reglas de oro
1. `core/` **nunca** importa nada de un SO ni de `platforms/`/`targets/`/`ui/`/`bridge/`.
2. Las librerías de SO se importan **de forma perezosa** (dentro de la factoría o del
   constructor del destino) para que el paquete se importe en cualquier plataforma.
3. Lo nuevo entra por extensión, no por modificación: un SO nuevo = una factoría;
   un destino nuevo = un módulo con `@register_target(..., platforms=...)`; una interfaz
   nueva = un módulo en `ui/` que use `PasteService`; una opción de menú = `MenuItem` + método.
4. Las interfaces nunca tocan adaptadores del SO: usan `PasteService` (`submit`, eventos).
5. Todo lo ajustable por el usuario va a `resources/default_config.toml` (comentado).
6. Nunca enviar Enter tras pegar: el usuario decide cuándo enviar.
7. Preferir canales **sin foco** (extensión, IPC de terminales) a enfocar + teclear.

## Comandos
```bash
python -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev,build]"   # Windows
.venv/Scripts/python -m pytest -q          # tests
.venv/Scripts/ruff check .                 # lint (ruff check --fix . para autoarreglar)
.venv/Scripts/python -m paste_photo                # bandeja
.venv/Scripts/python -m paste_photo run --debug    # consola con logs detallados
.venv/Scripts/python -m paste_photo doctor         # diagnóstico
.venv/Scripts/python -m paste_photo --probe        # ¿dónde pegaría? (no pega)
.venv/Scripts/python packaging/build.py            # .exe en dist/paste-photo
python3 packaging/linux/build_deb.py               # .deb (en Linux, con dpkg-deb)
```
Logs: `%LOCALAPPDATA%\paste-photo\logs` (Windows), `~/Library/Logs/paste-photo` (macOS),
`~/.local/state/paste-photo/logs` (Linux).
Config: `%APPDATA%\paste-photo\config.toml` / `~/Library/Application Support/paste-photo/` /
`~/.config/paste-photo/config.toml`.

## Convenciones
- **Nombre**: el producto se llama **PastePhoto** en todo lo que se ve (README, docs, bandeja,
  notificaciones, mensajes, instalador, accesos directos, `.desktop`, extensiones, winget
  `PackageName`, imágenes de marca). `paste-photo` es solo el **id técnico** y no se cambia:
  repositorio, comando y ejecutables (`paste-photo`, `paste-photo-cli`,
  `paste-photo-native-host`), paquete pip/.deb, `igarbayo.paste-photo` (winget), carpetas de
  configuración/registros, valor de inicio automático, `AppName` del instalador, ids de la
  extensión y del host. El módulo es `paste_photo`.
- Python ≥ 3.11, type hints en todo, `from __future__ import annotations`.
- Interfaces con `typing.Protocol` (no ABCs); dataclasses `frozen` para valores.
- `logging` (nunca `print`, salvo salida de CLI como `--probe`/`doctor`).
- Código, comentarios, mensajes y docs internas en **español**; `README.md` y `CONTRIBUTING.md` en **inglés** (cara pública del repo).
- Línea máx. 100; ruff con reglas `E,F,I,UP,B`.
- Tests del núcleo con fakes; lo que necesita escritorio real va a `tests/integration`.

## Verificación manual
**Windows**
1. `--probe` debe listar la pestaña de Claude Code.
2. Arrancar la bandeja, ir a otra app, Win+Shift+S → en el prompt de Claude aparece
   `[Image #N]` sin enviarse y el foco vuelve a la app original.
3. Comprobar en pantalla: el contenido de una pestaña de WT se lee por UI Automation
   (control `TermControl`, `TextPattern`); el menú de la bandeja, abriendo el desbordamiento.
⚠️ Si lo ejecutas desde una sesión de Claude Code, la imagen se pegará en **esa** sesión.

**Linux (desde Windows, con WSL2)** — receta probada:
- Distro Debian en WSL; usuario de prueba sin contraseña (creado como root, sin credenciales).
- Para X11 "real" usar **Xvfb + Openbox** (`DISPLAY=:99`): WSLg sirve para ver ventanas, pero
  su compositor ignora las peticiones de foco entre ventanas X → pruebas de foco engañosas.
- "Claude falso": copiar el binario de python3 con nombre `claude` y ejecutar un script que
  ponga el título `✳ ...` y registre en modo raw lo que recibe; Ctrl+V = byte `16`.
- Capturas: `xclip -selection clipboard -t image/png -i img.png`.
- Konsole necesita bus de sesión: `dbus-run-session -- bash prueba.sh`.
- Navegador: Chromium de Debian con `--load-extension` +
  `--disable-features=DisableLoadExtensionCommandLineSwitch`, copia de la extensión con URL
  `http://127.0.0.1/*` (misma `key` → mismo ID) y el manifiesto del host en
  `<user-data-dir>/NativeMessagingHosts`.
- Firefox: `firefox-esr` de Debian con perfil propio (`--profile <dir> --no-remote`) y
  `unset WAYLAND_DISPLAY`: si no, WSLg le da Wayland y su ventana no aparece en Xvfb.
- `/tmp` de Debian 13 es tmpfs y WSL apaga la distro entre llamadas: guardar en `$HOME`.
- ⚠️ **Espacio en C:**: el disco virtual de WSL y los perfiles de navegador de prueba crecen
  rápido. Con C: lleno la distro pasa a solo lectura (errores de E/S) y no arranca
  (`E_FAIL`): liberar espacio, `wsl --shutdown` y `dpkg --configure -a`. Mirar el espacio libre
  antes de instalar navegadores y borrar los perfiles de prueba al acabar.
- Desde Git Bash: `MSYS_NO_PATHCONV=1` antes de pasar rutas `/mnt/...` a `wsl.exe`, y escribir
  los scripts en archivos (la shell de la herramienta reduce las `\`).
- GNOME y KDE Wayland reales **no** se pueden probar así: quedan "Experimental".

**macOS** — probado en un Mac real por el usuario (todos los casos del README). El equipo de
desarrollo es Windows: lo que se puede probar sin un Mac va en CI (`macos-integration`:
portapapeles, carpeta de capturas, captura → tmux con un Claude falso, AppleScripts
compilados con `osacompile` contra Terminal, Safari y Chrome). Lo que necesita los permisos
de Accesibilidad o Automatización (foco, teclas, ejecutar AppleScript) no se puede conceder
en CI: un cambio ahí se verifica en un Mac (`paste-photo doctor`, `--probe`,
Cmd+Ctrl+Shift+4 y Cmd+Shift+4 con Claude en Terminal/iTerm2/Safari).
- Carpeta de capturas: `defaults read com.apple.screencapture location-last` (la elegida en
  Cmd+Shift+5 → Opciones; en el Mac del usuario, `~/Desktop/Screenshots`) **y** `location`.
  Leer solo `location` fue un fallo real: no está definida si el usuario solo usó Cmd+Shift+5.

## No tocar sin motivo
- `platforms/windows/focus.py`: `AttachThreadInput` + tecla virtual sin asignar (0xE8) para
  poder hacer `SetForegroundWindow`. **Nunca** usar Alt: abre menús en navegadores.
- Teclas de pegado: Windows Terminal **Alt+V**; Linux **Ctrl+V** (tabla en `targets/CLAUDE.md`).
- `platforms/linux/x11.py`: el teclado abre **una conexión X por pulsación** y sincroniza cada
  evento; con una conexión larga el Ctrl dejaba de aplicarse (mapa de teclado viejo).
