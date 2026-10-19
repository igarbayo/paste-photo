# ADR 0002: distribución en Windows (bandeja, PyInstaller, Inno Setup, winget)

- **Estado:** aceptada
- **Fecha:** 2026-10-19

## Contexto
paste-photo debe instalarse como un programa normal de Windows, correr en segundo plano con
una interfaz mínima y poder ampliarse (más opciones, más interfaces, más SO) sin rehacerlo.

## Decisión
- **Interfaz: icono en la bandeja** (`pystray` + `Pillow`), no una ventana: la app vive en
  segundo plano y el menú contextual cubre todo. `pystray` también funciona en macOS/Linux.
- **Motor compartido: `PasteService`.** Las interfaces (bandeja, consola, futuras) solo hablan
  con el servicio (métodos, `submit` y eventos). Un hilo de trabajo concentra todo lo que toca
  el SO (UI Automation/COM exige inicializarse por hilo).
- **Ejecutables: PyInstaller (onedir)**, dos `.exe` que comparten dependencias:
  `paste-photo.exe` (sin consola, bandeja) y `paste-photo-cli.exe` (consola).
  Onedir arranca más rápido que onefile y no se descomprime en `%TEMP%` en cada inicio.
- **Instalador: Inno Setup 6**, por usuario (`PrivilegesRequired=lowest`): no pide admin,
  se instala en `%LOCALAPPDATA%\Programs`, gestiona inicio automático y PATH. MSIX se
  descartó por exigir firma y empaquetado más complejo.
- **CI/CD: GitHub Actions.** `ci.yml` en cada push; `release.yml` al subir un tag `vX.Y.Z`.
  Una sola fuente de versión (`__version__`), comprobada contra el tag.
- **winget:** manifiestos generados en cada release (`InstallerType: inno`, `Scope: user`);
  envío a microsoft/winget-pkgs automatizado pero opcional (exige repo público).
- **Ajustes:** `config.toml` en `%APPDATA%`, creado desde la plantilla empaquetada; la
  bandeja lo modifica con `tomlkit` para no perder comentarios.

## Consecuencias
- ➕ Añadir una opción al menú, una interfaz o un SO no toca el núcleo ni el empaquetado.
- ➕ El mismo `packaging/build.py` construye en local y en CI.
- ➖ Sin certificado de firma, SmartScreen avisa en la primera ejecución.
- ➖ winget público y descargas para terceros requieren hacer público el repositorio.
