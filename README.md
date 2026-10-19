# paste-photo

<!-- Badges: register the project first, then uncomment.
     REUSE:      https://api.reuse.software/register
     OpenSSF BP: https://www.bestpractices.dev/en/projects/new (copy the badge from your project page)
     Scorecard:  https://scorecard.dev/
[![REUSE status](https://api.reuse.software/badge/github.com/igarbayo/paste-photo)](https://api.reuse.software/info/github.com/igarbayo/paste-photo)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/igarbayo/paste-photo/badge)](https://scorecard.dev/viewer/?uri=github.com/igarbayo/paste-photo)
-->

Take a screenshot and it shows up in Claude by itself.

paste-photo lives in the system tray. When you take a screenshot, it pastes the image into
the Claude you used last, without sending it, and puts you back where you were. It works on
**Windows and Linux**, in **any terminal** and in **any Chromium-based browser**.

## Features

- **Pastes into the Claude you are using**: Claude Code in a terminal, or any claude.ai chat
  (Chat, Code, Design) in the browser. If Claude is open in several places, the one you used
  last wins.
- **Never sends anything**: the image is attached to the prompt and you decide when to send.
- **Each screenshot is pasted once**: if you remove it, it does not come back.
- **Browser extension**: pastes into claude.ai without switching tabs, even into a background
  tab, on Windows, X11 and Wayland.
- **System tray icon**: pause or resume, choose where to paste, notifications, and start when
  you sign in.
- **`paste-photo doctor`** tells you what will work on your computer and how to fix what won't.

## Supported platforms

| System | Where Claude runs | How it pastes | Status |
|---|---|---|---|
| Windows 10/11 (x64) | Claude Code in Windows Terminal (also inside WSL) | focuses the tab, Alt+V | ✅ |
| Windows 10/11 (x64) | claude.ai in Chrome, Edge, Brave, Vivaldi, Opera | browser extension, or focus + Ctrl+V | ✅ |
| Linux (any) | Claude Code inside **tmux** | `tmux send-keys`, no focus needed | ✅ |
| Linux (any) | Claude Code in **kitty** (remote control on) or **WezTerm** | terminal's own CLI, no focus needed | ✅ |
| Linux (any) | Claude Code in **Konsole** | D-Bus, no focus needed | ✅ |
| Linux, X11 | Claude Code in **any other terminal** (GNOME Terminal, Ptyxis, xterm, Alacritty…) | focuses the window, Ctrl+V | ✅ |
| Linux, GNOME Wayland | Any other terminal | needs `paste-photo setup gnome` | ⚠️ Experimental |
| Linux, KDE Wayland | Any other terminal | KWin + permission prompt once | ⚠️ Experimental |
| Linux (any) | claude.ai in Chrome, Chromium, Edge, Brave, Vivaldi, Opera | browser extension | ✅ |
| macOS | Any | | Planned |

"Experimental" means it is implemented but has not been tested on a real desktop yet. Tell us
how it goes in an [issue](https://github.com/igarbayo/paste-photo/issues).

## Install

### Windows

**Installer (recommended).** Download `paste-photo-setup-X.Y.Z.exe` from
[Releases](https://github.com/igarbayo/paste-photo/releases) and run it. You can choose to
start paste-photo with Windows and to add `paste-photo-cli` to your PATH.

> The installer is not code-signed yet, so Windows SmartScreen may say "Windows protected
> your PC". Click **More info → Run anyway**.

**winget.** The package is under review in the public winget catalog. Once accepted:

```powershell
winget install igarbayo.paste-photo
```

### Linux

**Debian, Ubuntu, Mint…** Download `paste-photo_X.Y.Z_all.deb` from
[Releases](https://github.com/igarbayo/paste-photo/releases):

```bash
sudo apt install ./paste-photo_X.Y.Z_all.deb
```

**Any distribution, with pipx.** You also need `xclip` (X11) or `wl-clipboard` (Wayland),
which Claude Code itself uses to read pasted images:

```bash
pipx install --system-site-packages git+https://github.com/igarbayo/paste-photo
```

`--system-site-packages` lets the tray use your system's AppIndicator support (`python3-gi`).

Then check your setup:

```bash
paste-photo doctor
```

### Browser extension (optional, Windows and Linux)

The extension lets paste-photo paste into claude.ai without switching tabs, and also into
background tabs. Run this once:

```bash
paste-photo setup browser        # paste-photo-cli setup browser on Windows
```

It registers paste-photo with your browsers and prints a folder. Open `chrome://extensions`
(or `edge://extensions`, `brave://extensions`…), turn on **Developer mode**, click **Load
unpacked** and choose that folder.

### GNOME on Wayland

GNOME doesn't let apps see other windows. If your terminal isn't tmux, kitty, WezTerm or
Konsole, install the small GNOME Shell helper and sign out and back in once:

```bash
paste-photo setup gnome
```

### From source

```bash
git clone https://github.com/igarbayo/paste-photo.git
cd paste-photo
python -m venv .venv
.venv/bin/pip install -e .         # .venv\Scripts\pip on Windows
.venv/bin/paste-photo
```

## Use

1. Start **paste-photo** from your applications menu. Its icon appears in the system tray.
2. Open Claude: Claude Code in a terminal, or claude.ai in your browser.
3. Take a screenshot (**Win+Shift+S** on Windows, **PrtSc** or your usual tool on Linux). The
   image shows up in the Claude prompt (`[Image #1]` in the terminal). Add your message and
   send it whenever you want.

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
 ✔ Iniciar con Windows          ("Iniciar al iniciar sesión" on Linux)
 ─────────────────────────────
   Salir
```

### Command line

On Windows the installer includes `paste-photo-cli` for terminals; on Linux use `paste-photo`.

```bash
paste-photo doctor          # what works on this computer, and how to fix the rest
paste-photo --probe         # where the next screenshot would go (pastes nothing)
paste-photo run --debug     # run in the terminal with detailed logs (Ctrl+C to stop)
paste-photo setup browser   # register the browser extension
paste-photo setup gnome     # GNOME Wayland helper (Linux)
paste-photo --list-targets  # supported places where Claude can run
```

Sample `--probe` output, with Claude open in tmux and in the browser:

```text
1. browser_extension  -> 'New chat - Claude'
2. tmux               -> 'tmux %3'
```

## Configuration

The settings file is created the first time you run paste-photo, with every option
commented: `%APPDATA%\paste-photo\config.toml` on Windows, `~/.config/paste-photo/config.toml`
on Linux. Open it from the tray menu (**Abrir configuración**) and restart paste-photo after
editing it. Changes made from the tray menu apply right away.

The most useful options:

- `prefer = "recent"`: paste into the Claude you used last. `"order"` follows the order of
  the `[[targets]]` list instead.
- `title_regex`: only paste into a specific terminal tab, e.g. `"my-project"`.
- `enabled = false` on a `[[targets]]` entry turns that place off.

Logs: `%LOCALAPPDATA%\paste-photo\logs` on Windows, `~/.local/state/paste-photo/logs` on Linux
(tray menu: **Ver registro**).

### kitty

To paste without switching windows, enable kitty's remote control in `kitty.conf`:

```text
allow_remote_control socket-only
listen_on unix:@kitty
```

Without it, kitty is handled like any other terminal (Claude's tab has to be the active one).

## How it works

```text
 screenshot ──► clipboard / screenshot folder ──► orchestrator ──► most recently used Claude
                (new image only)                  (each image     ├─ browser extension (any tab)
                                                   pasted once)   ├─ tmux · kitty · WezTerm · Konsole
                                                                  │   (writes Ctrl+V into the pane)
                                                                  └─ any terminal: focus + Ctrl+V
                                                                     (Alt+V on Windows), focus back
```

The core does not depend on the operating system. Each OS, each place Claude can run and each
user interface (tray, console) is a separate piece, so new ones can be added without touching
the core.

## Troubleshooting

| Problem | Fix |
|---|---|
| Nothing gets pasted | Run `paste-photo doctor`. Check that the tray icon is there and not gray (paused). |
| I can't see the tray icon | Windows 11: look in the hidden area (`^`). GNOME: install the "AppIndicator and KStatusNotifierItem Support" extension. |
| "paste-photo ya se está ejecutando" (already running) | Only one instance runs at a time. Use the one in the tray, or quit it first. |
| It pastes in the wrong place | Click into the Claude you want before taking the screenshot, or set `prefer = "order"`. |
| The browser extension doesn't connect | Run `paste-photo setup browser` again and reload the extension. Chromium installed as a **snap** restricts this; use the .deb/.rpm build of your browser. |
| Linux: nothing happens in GNOME Terminal on Wayland | Run `paste-photo setup gnome` and sign out and in, or use tmux. |
| Linux: the image never reaches Claude Code | Install `xclip` (X11) or `wl-clipboard` (Wayland); Claude Code needs it to read images. |
| "Windows protected your PC" | The installer is not code-signed yet: **More info → Run anyway**. |

## Uninstall

- **Windows**: **Settings → Apps → Installed apps → paste-photo → Uninstall**. This removes the
  start with Windows entry and the PATH entry.
- **Linux**: `sudo apt remove paste-photo` or `pipx uninstall paste-photo`. Turn off "Iniciar al
  iniciar sesión" first, or delete `~/.config/autostart/paste-photo.desktop`.

Your settings are kept in both cases.

## License

paste-photo is released under the [MIT License](LICENSE). It is provided **without any
warranty**. The installers bundle third-party components under their own licenses (MIT, BSD,
Apache-2.0, PSF and LGPL-3.0 for pystray). Their notices ship with the app. See
[docs/COMPONENTS_LICENSE.md](docs/COMPONENTS_LICENSE.md) for the full analysis.

paste-photo is an independent project, not affiliated with or endorsed by Anthropic.
"Claude" is a trademark of Anthropic and is only used here to describe what paste-photo
works with.

## Support

Open an [issue](https://github.com/igarbayo/paste-photo/issues). Contributions are welcome:
see [CONTRIBUTING.md](CONTRIBUTING.md). Changes are listed in [CHANGELOG.md](CHANGELOG.md).
