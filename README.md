# paste-photo

<!-- Badges: register the project first, then uncomment.
     REUSE:      https://api.reuse.software/register
     OpenSSF BP: https://www.bestpractices.dev/en/projects/new (copy the badge from your project page)
     Scorecard:  https://scorecard.dev/ (needs a public repo)
[![REUSE status](https://api.reuse.software/badge/github.com/igarbayo/paste-photo)](https://api.reuse.software/info/github.com/igarbayo/paste-photo)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/igarbayo/paste-photo/badge)](https://scorecard.dev/viewer/?uri=github.com/igarbayo/paste-photo)
-->

Take a screenshot and it shows up in Claude by itself.

paste-photo lives in the system tray. When you take a screenshot, it pastes the image into
the Claude you used last, without sending it, and puts you back where you were.

## Features

- **Pastes into the Claude you are using**: Claude Code in Windows Terminal, or any claude.ai
  chat (Chat, Code, Design) in Chrome or Edge. If Claude is open in several places, the one
  you used last wins.
- **Never sends anything**: the image is attached to the prompt and you decide when to send.
- **Each screenshot is pasted once**: if you remove it, it does not come back.
- **System tray icon**: pause or resume, choose where to paste, notifications, and start with
  Windows.
- **Windows installer**: per-user install with no admin rights, plus an uninstaller.

## Supported platforms

| System | Where Claude runs | Status |
|---|---|---|
| Windows 10/11 (x64) | Claude Code in Windows Terminal (also inside WSL) | ✅ |
| Windows 10/11 (x64) | claude.ai (Chat, Code, Design) in Chrome, Edge, Brave, Vivaldi or Opera | ✅ |
| Windows 10/11 | Firefox, the Claude desktop app, VS Code | Planned |
| macOS, Linux | Any | Planned |

## Install

**Installer (recommended).** Download `paste-photo-setup-X.Y.Z.exe` from
[Releases](https://github.com/igarbayo/paste-photo/releases) and run it. You can choose to
start paste-photo with Windows and to add `paste-photo-cli` to your PATH.

> The installer is not code-signed yet, so Windows SmartScreen may say "Windows protected
> your PC". Click **More info → Run anyway**.

**winget.** Every release includes winget manifests (`winget-manifests-X.Y.Z.zip`). The
package is not in the public winget catalog yet. Once it is, installing will be:

```powershell
winget install igarbayo.paste-photo
```

**From source** (Python 3.11+):

```bash
git clone https://github.com/igarbayo/paste-photo.git
cd paste-photo
python -m venv .venv
.venv\Scripts\python -m pip install -e .
.venv\Scripts\python -m paste_photo
```

## Use

1. Open **paste-photo** from the Start menu. Its icon appears in the system tray. On
   Windows 11 new icons go to the hidden area (`^`); drag it to the taskbar to keep it in view.
2. Open Claude: Claude Code in Windows Terminal, or claude.ai in your browser.
3. Press **Win+Shift+S** and select an area. The image shows up in the Claude prompt
   (`[Image #1]` in the terminal). Add your message and send it whenever you want.

Right-click the tray icon:

```text
 paste-photo: activo
 ─────────────────────────────
 ✔ Activado                     pause / resume (the icon turns gray when paused)
   Pegar en ▸                   the Claude you used last | the order in the config
 ✔ Notificaciones
 ─────────────────────────────
   ¿Dónde pegaría ahora?        shows where the next screenshot would go
   Abrir configuración
   Ver registro
 ✔ Iniciar con Windows
 ─────────────────────────────
   Salir
```

### Command line

The installer includes `paste-photo-cli` for terminals. From source, use `python -m paste_photo`.

```bash
paste-photo-cli --probe          # where the next screenshot would go (pastes nothing)
paste-photo-cli run --debug      # run in the terminal with detailed logs (Ctrl+C to stop)
paste-photo-cli --list-targets   # supported places where Claude can run
paste-photo-cli --version
```

Sample `--probe` output, with Claude open in both the terminal and the browser:

```text
1. windows_terminal   -> '✳ my-project'
2. browser            -> 'New chat - Claude'
```

## Configuration

The settings file is `%APPDATA%\paste-photo\config.toml`, created the first time you run
paste-photo. Every option is commented. Open it from the tray menu (**Abrir configuración**)
and restart paste-photo after editing it. Changes made from the tray menu apply right away.

The most useful options:

- `prefer = "recent"`: paste into the Claude you used last. `"order"` follows the order of
  the `[[targets]]` list instead.
- `title_regex`: only paste into a specific terminal tab, e.g. `"my-project"`.
- `browsers`: which browsers to look in.

Logs are in `%LOCALAPPDATA%\paste-photo\logs` (tray menu: **Ver registro**).

## How it works

```text
 screenshot ──► clipboard listener ──► orchestrator ──► most recently used Claude
 (Win+Shift+S)   (new image only)      (each image      ├─ Windows Terminal tab  (Alt+V)
                                        pasted once)    └─ claude.ai browser tab (Ctrl+V)
                                                           then focus goes back to you
```

The core does not depend on the operating system. Each OS, each place Claude can run and
each user interface (tray, console) is a separate piece, so new ones can be added without
touching the core.

## Troubleshooting

| Problem | Fix |
|---|---|
| Nothing gets pasted | Check that the tray icon is there and not gray (paused). Use **¿Dónde pegaría ahora?** or `paste-photo-cli --probe` to see whether it finds Claude. |
| I can't see the tray icon | On Windows 11 it may be in the hidden area (`^`) next to the clock. |
| "paste-photo ya se está ejecutando" (already running) | Only one instance runs at a time. Use the one in the tray, or quit it first. |
| It pastes in the wrong place | Click into the Claude you want before taking the screenshot, or set `prefer = "order"`. |
| A browser tab is not detected | Background tabs are matched by their title. A Claude Design project is only detected while its tab is visible. |
| "Windows protected your PC" | The installer is not code-signed yet: **More info → Run anyway**. |

## Uninstall

Use **Settings → Apps → Installed apps → paste-photo → Uninstall**. This removes the start
with Windows entry and the PATH entry. Your settings in `%APPDATA%\paste-photo` are kept.

## Support

Open an [issue](https://github.com/igarbayo/paste-photo/issues). Contributions are welcome:
see [CONTRIBUTING.md](CONTRIBUTING.md). Changes are listed in [CHANGELOG.md](CHANGELOG.md).
