# paste-photo

<!-- Badges: register the project first, then uncomment.
     REUSE:      https://api.reuse.software/register
     OpenSSF BP: https://www.bestpractices.dev/en/projects/new
     Scorecard:  https://scorecard.dev/ (needs a public repo)
[![REUSE status](https://api.reuse.software/badge/github.com/igarbayo/paste-photo)](https://api.reuse.software/info/github.com/igarbayo/paste-photo)
     OpenSSF Best Practices: copy the badge markdown from your project page once registered.
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/igarbayo/paste-photo/badge)](https://scorecard.dev/viewer/?uri=github.com/igarbayo/paste-photo)
-->

Take a screenshot and it shows up in Claude by itself.

paste-photo watches for new screenshots. When Claude is open, it pastes the image into
the Claude you used last, without sending it, and puts you back where you were.

## Supported platforms

| System | Where Claude runs | Status |
|---|---|---|
| Windows 10/11 | Claude Code in Windows Terminal (also inside WSL) | ✅ |
| Windows 10/11 | Any claude.ai chat (Chat, Code, Design) in Chrome, Edge or another Chromium browser | ✅ |
| macOS, Linux | Any | Planned |

## Quick start

```bash
git clone https://github.com/igarbayo/paste-photo.git
cd paste-photo
python -m venv .venv
.venv\Scripts\python -m pip install -e .
.venv\Scripts\python -m paste_photo
```

Then press **Win+Shift+S** and select an area. In the terminal the image appears as
`[Image #1]` in the Claude Code prompt. Add your message and send it whenever you want.

## Examples

```bash
python -m paste_photo                 # listen until Ctrl+C
python -m paste_photo --probe         # show where the next screenshot would go (pastes nothing)
python -m paste_photo --debug         # verbose logs
python -m paste_photo --config my.toml
```

Sample `--probe` output, with Claude open in both the terminal and the browser:

```text
1. windows_terminal   -> '✳ my-project'
2. browser            -> 'New chat - Claude'
```

## How it works

```text
 screenshot ──► clipboard listener ──► orchestrator ──► most recently used Claude
 (Win+Shift+S)   (new image only)      (each image      ├─ Windows Terminal tab  (Alt+V)
                                        pasted once)    └─ claude.ai browser tab (Ctrl+V)
                                                           then focus goes back to you
```

The core does not depend on the operating system. Each OS and each place Claude can run
is a separate adapter, so new ones can be added without touching the core.

## Configuration

Settings live in [`config.toml`](config.toml), and every option is commented there. The most
useful ones:

- `prefer = "recent"`: paste into the Claude you used last (`"order"` follows the list order instead).
- `title_regex`: only paste into a specific tab, e.g. `"my-project"`.

## Troubleshooting

| Problem | Fix |
|---|---|
| Nothing gets pasted | Make sure paste-photo is running. Run `--probe` to see whether it finds Claude. |
| `paste-photo ya se está ejecutando` (already running) | Only one instance is allowed at a time. Close the other one. |
| It pastes in the wrong place | Use the Claude you want right before taking the screenshot, or set `prefer = "order"`. |
| A browser tab is not detected | Background tabs are matched by title. A Claude Design project is only detected while it is the visible tab. |

## Support

Open an [issue](https://github.com/igarbayo/paste-photo/issues). Contributions are welcome:
see [CONTRIBUTING.md](CONTRIBUTING.md). Changes are listed in [CHANGELOG.md](CHANGELOG.md).
