# packaging/: distribución

Recuerda la regla obligatoria del CLAUDE.md raíz: todo cambio lleva entrada en `CHANGELOG.md`.

```
packaging/
  build.py               punto de entrada único (local y CI): .exe y, con --installer, instalador;
                         en macOS, PastePhoto.app y, con --dmg, el .dmg
  make_icon.py           genera paste_photo/resources/icon.png e icon.ico (--icns:
                         packaging/macos/icon.icns, se genera al construir y no se guarda)
  make_brand.py          docs/assets/logo.png (README) y social-preview.png (1280x640, se
                         sube a mano en Settings → Social preview) a partir del icono
  demo/demo.py           graba docs/assets/demo.gif con PastePhoto y Claude Code reales
                         (Windows; ver "Demo del README")
  release_notes.py       sección de una versión del CHANGELOG (notas de la release)
  firefox_xpi.py         .xpi de Firefox a partir de la extensión de Chromium (+ carpeta
                         para `web-ext sign`)
  windows/
    paste-photo.spec     PyInstaller: paste-photo.exe (bandeja), paste-photo-cli.exe (consola)
                         y paste-photo-native-host.exe (lo lanza el navegador)
    entry.py             script de entrada común: el nombre del .exe decide el papel
    installer.iss        Inno Setup 6, por usuario
  macos/
    paste-photo.spec     PyInstaller + BUNDLE: PastePhoto.app con paste-photo (barra de menús
                         y CLI) y paste-photo-native-host en Contents/MacOS (usa
                         windows/entry.py)
    rthook_env.py        hook de arranque: PATH de Homebrew y LANG (Finder no los da)
  winget/
    make_manifests.py    manifiestos de winget (igarbayo.paste-photo)
  linux/
    build_deb.py         .deb `all`: paquete en /usr/lib/paste-photo, pystray vendorizado,
                         resto de dependencias de Debian (Depends), lanzadores en /usr/bin
.github/workflows/
  ci.yml                 lint + tests (Windows, macOS y Linux), integración X11 (Xvfb) y
                         macOS (runner real), .exe, .deb y .app/.dmg
  release.yml            tag vX.Y.Z → .deb + zip de la extensión + .xpi de Firefox (job
                         linux) y .dmg (job macos) → instalador, sha256 y manifiestos
                         (job release) → GitHub Release (+ winget)
```

## Versión: una sola fuente
`paste_photo/__init__.py` → `__version__`. La leen `build.py` (propiedades del `.exe`,
nombre del instalador), el instalador (`/DAppVersion`) y la release (el tag **debe** ser
`v<__version__>`; si no, la release falla a propósito).

## Publicar una versión
1. `[Unreleased]` del CHANGELOG → `## [X.Y.Z] - AAAA-MM-DD` (+ enlaces del pie).
2. `__version__ = "X.Y.Z"`.
3. Commit + push a `main`, esperar a que CI esté en verde.
4. `git tag vX.Y.Z && git push origin vX.Y.Z` → `release.yml` publica la release.
`tests/test_packaging.py` comprueba que la versión actual tiene sección en el CHANGELOG.

## Construir en local
```bash
.venv/Scripts/python -m pip install -e ".[build]"
.venv/Scripts/python packaging/build.py              # dist/paste-photo/
.venv/Scripts/python packaging/build.py --installer  # + dist/paste-photo-setup-X.Y.Z.exe (Inno Setup 6)
```
`build.py` hace una prueba de humo del `.exe` (versión y destinos registrados).

## Trampas
- **Plugins**: destinos y plataformas se importan por nombre → `collect_submodules("paste_photo")`
  en el spec. Un módulo nuevo no necesita tocar el spec.
- **Recursos**: se leen con `paste_photo.resources` (`importlib.resources`); el spec los
  incluye con `collect_data_files("paste_photo")`. Nuevos tipos de archivo: añadirlos también
  a `[tool.setuptools.package-data]` en `pyproject.toml`.
- `uiautomation` carga sus DLL por ctypes: PyInstaller avisa "not found" pero las copia como
  datos en `_internal/uiautomation/bin`. Verificado con `paste-photo-cli.exe --probe`.
- `paste-photo.exe` no tiene consola: `sys.stdout`/`stderr` son `None`. Para mensajes al
  usuario sin consola, ventana nativa (ver `_tell_user_already_running`).
- El instalador y la bandeja comparten el valor de registro `HKCU\...\Run\paste-photo`.
- **SmartScreen**: sin certificado de firma de código, Windows avisa la primera vez.

## winget
- Manifiestos 1.6.0, `InstallerType: inno`, `Scope: user`, `Commands: paste-photo-cli`.
- Validar: `winget validate --manifest <carpeta de la versión>` (no requiere admin).
- Envío automático (`release.yml`, job `winget`): requiere **repo público**, variable
  `WINGET_SUBMIT=true` y secreto `WINGET_TOKEN` (ya configurados; el repo es público).
  La primera PR fue microsoft/winget-pkgs#456268 (0.2.1). El primer envío falló porque
  wingetcreate acababa de crear el fork `igarbayo/winget-pkgs`: relanzar el job basta.
- `License: MIT` (+ `LicenseUrl`, `Copyright`). Si cambia la licencia, actualizar `make_manifests.py`.

## Demo del README
`.venv/Scripts/python packaging/demo/demo.py` (Windows, pantalla principal 1920x1080,
Claude Code instalado; ~40 s sin tocar ratón ni teclado). Abre la escena (fondo, app de
facturas de `demo/scene_windows.py`, Windows Terminal "PastePhoto demo" con Claude Code en
`~/invoice-app`), arranca PastePhoto limitado a ese título, escribe la pregunta, hace la
captura real con Win+Shift+S y monta `docs/assets/demo.gif`; luego cierra todo sin enviar.
- Si se lanza desde una sesión de Claude Code, la terminal nueva se abre **sin** las variables
  `CLAUDE*` (si no, Claude Code muestra avisos en la cabecera).
- La captura de Windows no incluye el puntero ni el rectángulo de Recortes: se dibujan con la
  posición real del ratón (`build_gif`).
- Coordenadas en píxeles físicos (proceso con DPI por monitor): `APP_RECT`, `TERM_RECT`,
  `REGION`. Con otra resolución, ajustarlas.

## Firefox: .xpi y firma
- `python packaging/firefox_xpi.py dist/paste-photo-firefox-X.Y.Z.xpi` (cualquier SO).
- Firefox normal solo instala extensiones firmadas. Con los secretos `AMO_JWT_ISSUER` y
  `AMO_JWT_SECRET` (cuenta de addons.mozilla.org → *Manage API Keys*), la release la firma con
  `npx web-ext@8 sign --channel=unlisted` (no se publica en el catálogo). Sin ellos, avisa y
  publica el `.xpi` sin firmar. AMO no deja firmar dos veces la misma `version`.

## Linux: .deb y pipx
- `python3 packaging/linux/build_deb.py` (Linux, `dpkg-deb`, pystray instalado en ese Python).
- El lanzador `/usr/bin/paste-photo` exporta `PYTHONPATH` y `PASTE_PHOTO_LAUNCH` (orden de
  inicio automático). Probado: `apt install ./paste-photo_X_all.deb` en Debian 13 y en CI.
- pipx: `pipx install --system-site-packages ...` (AppIndicator vía `python3-gi` del sistema).

## macOS: .app y pipx
- `python packaging/build.py --dmg` (en macOS, con `.[build]`): `dist/PastePhoto.app` y
  `dist/PastePhoto-X.Y.Z-macos-<arch>.dmg` (`hdiutil`, con enlace a /Applications). Solo
  para la arquitectura del runner: `macos-latest` es arm64. Intel: pipx.
- Prueba de humo: `--version`, `--list-targets` (`terminal_app`, `browser_extension`), host
  nativo con stdin cerrado y `codesign --verify`. Lo que pide permisos (bandeja, foco,
  AppleScript) **no** se prueba en CI: verificar en un Mac real; hasta entonces, "Experimental".
- **Firma**: PyInstaller firma ad hoc; `third_party.write_notices` escribe en
  `Contents/Resources` después y rompe el sello → `build.py` vuelve a firmar ad hoc
  (`codesign --force --deep --sign -`). Sin Developer ID ni notarización, Gatekeeper bloquea
  la primera apertura ("Abrir igualmente" o `xattr -dr com.apple.quarantine`).
- **Permisos (TCC)**: con el `.app`, Accesibilidad y Automatización van a la app
  (`io.github.igarbayo.paste-photo`), no al Python ni a la terminal. Con firma ad hoc el
  permiso va ligado al hash del binario: cada versión nueva hay que quitarla y volver a
  añadirla en Accesibilidad. Se arregla con un Developer ID (siguiente paso: cuenta de Apple
  Developer, `codesign` con hardened runtime + `notarytool`, secretos en GitHub).
- `NSAppleEventsUsageDescription` en el `Info.plist`: el texto del aviso de Automatización.
- pipx: `pipx install git+https://github.com/igarbayo/paste-photo` (pyobjc llega como
  dependencia con marcador `darwin`).

## Otro SO (futuro)
`build.py` sale con error fuera de Windows y macOS (Linux usa `linux/build_deb.py`). Para
otro SO: añadir `packaging/<so>/` y una rama en `build.py`, más un job en `release.yml`.
