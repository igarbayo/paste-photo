# Components and licensing

This document explains which license paste-photo uses, why, and how that license fits with
every library, tool, binary and asset the project depends on. It is written for people: if you
want to reuse paste-photo, contribute to it or redistribute it, start here.

> **Short version.** paste-photo's own code is under the **MIT License**. Every component it
> depends on is either permissive (MIT, BSD, Apache-2.0, PSF…) or, in one case, **LGPL-3.0**
> (pystray), which allows being used by MIT code. The Windows installer bundles third-party
> binaries, so it ships their license texts and keeps pystray replaceable, as the LGPL requires.

All information below was checked on 2026-10-19 against the installed packages (their
`License`/`License-Expression` metadata and the license files inside each package), the
contents of the built `.exe` folder and Pillow's SBOM. The versions are those of release 0.2.x.

## 1. The license we chose: MIT

**Decision:** MIT License, `Copyright (c) 2026 igarbayo`, in [`LICENSE`](../LICENSE) and
[`LICENSES/MIT.txt`](../LICENSES/MIT.txt).

Why MIT:

- **It is compatible with every component.** No dependency is under a strong copyleft license
  (GPL/AGPL) that would force the whole project to adopt it (see section 3).
- **It is the simplest option for a small, single-maintainer tool.** Anyone can use, modify and
  redistribute it, including in commercial or closed products, as long as they keep the
  copyright notice.
- **Maximum adoption and easy packaging.** Package managers such as winget accept MIT without
  extra review, and the license text fits in one screen.
- **No patent clause needed.** paste-photo does not implement patentable techniques. If that
  ever changes, Apache-2.0 would be the natural upgrade, since it is compatible with the same
  components.

Like every open source license, MIT provides the software **without any warranty**.

### Licenses we considered

| License | Possible? | Why not |
|---|---|---|
| Apache-2.0 | Yes | More text and NOTICE handling for no practical gain here (no patents involved). |
| BSD-3-Clause | Yes | Practically the same as MIT; MIT is better known. |
| GPL-3.0 | Yes | Would force derivative works to be GPL, which discourages reuse of a small utility. |
| AGPL-3.0 | Yes, but pointless | paste-photo is a desktop app, not a network service. |
| Proprietary | — | Rejected: the goal is an open project published on winget. |

## 2. Inventory of components

### 2.1 Runtime Python dependencies (imported by paste-photo)

These are resolved automatically from `pyproject.toml` (`Requires-Dist`, Windows markers)
by `packaging/third_party.py`.

| Component | Version | License (SPDX) | What we use it for | Bundled in the installer? |
|---|---|---|---|---|
| [pywin32](https://github.com/mhammond/pywin32) | 312 | PSF-2.0 | Clipboard listener, windows, focus, registry | Yes |
| [uiautomation](https://github.com/yinkaisheng/Python-UIAutomation-for-Windows) | 2.0.29 | Apache-2.0 | Finding Windows Terminal and browser tabs, prompt editor | Yes, incl. its `UIAutomationClient_VC140_*.dll` |
| [comtypes](https://github.com/enthought/comtypes) | 1.4.17 | MIT | COM layer used by uiautomation | Yes |
| [psutil](https://github.com/giampaolo/psutil) | 7.2.2 | BSD-3-Clause | Is a `claude` process alive under a terminal window? | Yes |
| [pystray](https://github.com/moses-palmer/pystray) | 0.19.5 | **LGPL-3.0-or-later** | System tray icon and menu | Yes, **as replaceable source files** |
| [six](https://github.com/benjaminp/six) | 1.17.0 | MIT | Dependency of pystray | Yes |
| [Pillow](https://github.com/python-pillow/Pillow) | 13.0.0 | MIT-CMU (HPND) | Tray icon images, generating the app icon | Yes (see 2.2) |
| [tomlkit](https://github.com/python-poetry/tomlkit) | 0.15.2 | MIT | Saving tray settings without losing comments | Yes |

Linux-only dependencies (`sys_platform == 'linux'` markers):

| Component | Version | License (SPDX) | What we use it for | How it reaches users |
|---|---|---|---|---|
| [python-xlib](https://github.com/python-xlib/python-xlib) | 0.33 | **LGPL-2.1-or-later** | X11 windows (EWMH), XTEST keys, XFixes clipboard events | pip/pipx dependency; on Debian, the system package `python3-xlib` (not bundled) |
| [jeepney](https://gitlab.com/takluyver/jeepney) | 0.9.0 | MIT | D-Bus: Konsole, GNOME Shell helper, KWin scripts, RemoteDesktop portal | pip/pipx dependency; on Debian, `python3-jeepney` (not bundled) |

The `.deb` uses Debian's own packages for Pillow, psutil, python-xlib, jeepney, tomlkit and
six (declared in `Depends`), so it does not redistribute them. It only ships **pystray**,
which Debian doesn't package, as unmodified source in `/usr/lib/paste-photo/vendor/pystray`.

### 2.2 Native binaries inside the Windows distribution

The `.exe` folder (`dist/paste-photo/_internal`) also contains compiled code. These are the
binaries actually present in the build, and their licenses:

| Binary | Comes from | License |
|---|---|---|
| `python312.dll`, `python3.dll`, `*.pyd` | CPython 3.12 | PSF-2.0 |
| `libssl-3.dll`, `libcrypto-3.dll` | OpenSSL 3 (via CPython) | Apache-2.0 |
| `libffi-8.dll` | libffi (via CPython) | MIT |
| `_bz2.pyd`, `_lzma.pyd`, `pyexpat.pyd`, `_decimal.pyd` | bzip2, xz, expat, mpdecimal | bzip2-1.0.6, 0BSD/PD, MIT, BSD-2-Clause |
| `VCRUNTIME140*.dll`, `ucrtbase.dll`, `api-ms-win-*.dll` | Microsoft Visual C++ Runtime / Universal CRT | Microsoft redistributable code |
| `pywintypes312.dll`, `win32*.pyd` | pywin32 | PSF-2.0 |
| `UIAutomationClient_VC140_X64/X86.dll` | uiautomation | Apache-2.0 |
| `_psutil_windows.pyd` | psutil | BSD-3-Clause |
| `PIL/_imaging*.pyd`, `_webp`, `_avif` | Pillow, statically linked with the libraries below | MIT-CMU + each library's license |

Native libraries **inside Pillow's Windows wheel** (checked with `PIL.features`):

| Library | Included? | License |
|---|---|---|
| libjpeg-turbo 3.2.0 | Yes | IJG + BSD-3-Clause |
| zlib-ng 2.3.3 | Yes | Zlib |
| libwebp 1.6.0 | Yes | BSD-3-Clause |
| libavif 1.4.2 | Yes | BSD-2-Clause |
| Little CMS 2.19 | Yes | MIT |
| OpenJPEG 2.5.4 | Yes | BSD-2-Clause |
| libtiff 4.7.2 | Yes | libtiff (permissive) |
| FreeType 2.14.3 | In the wheel, **not in our build** (`ImageFont` is never imported) | FTL or GPL-2.0 |
| libimagequant | **No** | GPL-3.0-or-later |
| FriBiDi, raqm, HarfBuzz, libxcb | **No** | LGPL-2.1+, MIT, MIT, X11 |

Pillow's own license file (shipped in `licenses/pillow/LICENSE`) contains the full texts of
the libraries it bundles.

### 2.3 Build, test and release tools (not distributed)

These are used to *make* paste-photo but are not part of what users install, except where
noted.

| Tool | License | Notes |
|---|---|---|
| [PyInstaller](https://pyinstaller.org) 6.x | GPL-2.0-or-later **with bootloader exception** | The exception explicitly allows bundling programs under any license. Its bootloader is part of the `.exe`; we still ship its license in `licenses/pyinstaller/`. |
| pyinstaller-hooks-contrib | GPL-2.0-or-later / Apache-2.0 | Build-time hooks only. |
| [Inno Setup 6](https://jrsoftware.org/isinfo.php) | Inno Setup License (permissive) | Free for any use, including commercial. Its setup stub runs the installer. |
| setuptools, packaging | MIT, Apache-2.0 OR BSD-2-Clause | Packaging metadata. |
| pytest, ruff | MIT | Tests and lint. |
| GitHub Actions (`actions/checkout`, `actions/setup-python`, `actions/upload-artifact`) | MIT | CI only. |
| Chocolatey, wingetcreate | Apache-2.0, MIT | Release job only. |
| [web-ext](https://github.com/mozilla/web-ext) 8.x | MPL-2.0 | Release job only: sends the Firefox `.xpi` to addons.mozilla.org to be signed. Not distributed; the signed `.xpi` contains only our own files. |

### 2.4 Assets and content

| Asset | Origin | License |
|---|---|---|
| App icon (`paste_photo/resources/icon.png`, `icon.ico`) | Drawn by code in `packaging/make_icon.py` (original work) | MIT, like the rest of the project |
| Default configuration (`default_config.toml`) | Original | MIT |
| Browser extension (`resources/extension/`, incl. `icon128.png`) | Original | MIT |
| GNOME Shell helper (`resources/gnome_extension/`) | Original | MIT (compatible with the GPL-2.0-or-later that extensions.gnome.org expects) |
| Documentation | Original | MIT |

### 2.5 Trademarks and services

paste-photo mentions **Claude**, **Claude Code**, **claude.ai**, **Windows**, **Chrome**,
**Edge** and **Firefox** only to describe what it works with (nominative use). paste-photo is
an independent project and is **not affiliated with, endorsed by or sponsored by Anthropic,
Microsoft, Google or Mozilla**. It does not use their logos, and its icon is original. It does not call any Claude
API and does not send data anywhere: it only simulates the paste shortcut on the local machine.

## 3. Compatibility analysis

How each license family interacts with MIT:

- **Permissive (MIT, MIT-CMU, BSD-2/3, Zlib, IJG, libtiff, PSF-2.0, Apache-2.0).** They can be
  combined with MIT code freely. Their only real requirement is to **keep their copyright
  notices and license texts** when redistributing. Apache-2.0 also asks to keep any `NOTICE`
  file; uiautomation and OpenSSL do not ship one beyond what is already in their texts.
- **LGPL-3.0 (pystray).** The LGPL is designed for libraries: an MIT program may *use* an
  LGPL library without becoming LGPL itself. paste-photo only imports pystray and does not
  modify it, so the repository stays MIT. **Redistributing** pystray inside the installer adds
  obligations, covered in section 4.
- **LGPL-2.1 (python-xlib, Linux).** Same reasoning: paste-photo imports it unmodified. It is
  never bundled: pip/pipx install it from PyPI and the `.deb` depends on Debian's
  `python3-xlib`, so users get it, its source and its license from those channels.
- **GPL-2.0 with bootloader exception (PyInstaller).** The exception exists precisely so that
  bundled apps can use any license. No obligation for paste-photo's code.
- **GPL / LGPL components we do not ship.** Pillow's Windows wheel excludes libimagequant
  (GPL-3.0) and FriBiDi (LGPL-2.1), and our build does not include FreeType. If a future Pillow
  build or a new import (for example `ImageFont`) brings them in, re-check this section: GPL
  code inside the installer would require distributing the whole binary under GPL terms.
- **Microsoft runtime.** The Visual C++ Runtime and Universal CRT DLLs are "distributable
  code" that Microsoft allows apps to ship alongside them.

**Conclusion:** MIT is valid for the repository and for the installer, provided the
obligations below are met. They are met automatically by the build.

## 4. Obligations when distributing the installer, and how we meet them

| Obligation | Source | How paste-photo meets it |
|---|---|---|
| Keep copyright notices and license texts of bundled components | MIT, BSD, PSF, Apache-2.0, Zlib, IJG… | `packaging/third_party.py` copies every license file into `licenses/<component>/` and writes `THIRD-PARTY-NOTICES.txt` next to the `.exe`. The installer copies both. |
| Give a prominent notice that pystray is used and is under the LGPL, plus the LGPL and GPL texts | LGPL-3.0 §4(a)(b) | Section "pystray (LGPL-3.0-or-later)" in `THIRD-PARTY-NOTICES.txt`; `licenses/pystray/COPYING.LGPL` and `COPYING`. |
| Let the user replace pystray with a modified version | LGPL-3.0 §4(d) | The PyInstaller spec uses `module_collection_mode={"pystray": "py"}`, so pystray ships as plain `.py` files in `_internal/pystray/`, loaded at runtime. `build.py` fails if they are missing. |
| Make pystray's source available | LGPL-3.0 §4(d)(0) | The shipped files *are* the unmodified source; upstream link in the notices. |
| Not forbid reverse engineering for debugging pystray modifications | LGPL-3.0 §4 | MIT imposes no such restriction. |
| Include paste-photo's own license | MIT | `LICENSE` at the root of the app folder; shown on the installer's license page. |

Example: after installing, `%LOCALAPPDATA%\Programs\paste-photo\` contains:

```text
LICENSE                    paste-photo (MIT)
THIRD-PARTY-NOTICES.txt    what is bundled and under which license
licenses\pystray\COPYING.LGPL
licenses\python\LICENSE.txt   CPython + OpenSSL, libffi, bzip2...
_internal\pystray\*.py     replaceable LGPL library
```

### The Linux `.deb`

| Obligation | How the `.deb` meets it |
|---|---|
| paste-photo's license | `/usr/share/doc/paste-photo/copyright` (Debian machine-readable format, MIT). |
| pystray: notice, license, replaceable source | Same `copyright` file declares `vendor/pystray/*` as LGPL-3+ (full text in `/usr/share/common-licenses/LGPL-3` on every Debian system); pystray ships as unmodified `.py` files in `/usr/lib/paste-photo/vendor/pystray`, which users can replace. |
| Other dependencies | Not redistributed: declared as Debian `Depends` and installed from the distribution, with their own `copyright` files. |

## 5. Adding or updating a dependency

1. Check its license **before** adding it:
   ```bash
   python -c "import importlib.metadata as m; d=m.metadata('NAME'); print(d.get('License-Expression') or d.get('License'))"
   ```
2. Permissive or LGPL: fine. **GPL or AGPL:** do not add it without discussing it in an
   issue, because it would change the license of the installer.
3. Add it to `pyproject.toml`. `packaging/third_party.py` picks up its license files
   automatically on the next build.
4. If it is LGPL, add it to `module_collection_mode` in `packaging/windows/paste-photo.spec`
   and add a notice like pystray's in `third_party.py`. For Linux, prefer the Debian package
   in `DEPENDS` (`packaging/linux/build_deb.py`); if you must vendor it, add a `Files:` stanza
   to the `.deb` copyright text.
5. If it ships native libraries (like Pillow), list them in section 2.2.
6. Update this document and the CHANGELOG.

`tests/test_packaging.py` checks that the notices are generated and that pystray's LGPL text
is included.

## 6. SPDX identifiers

- Project: `MIT` (`pyproject.toml`: `license = "MIT"`; text in `LICENSES/MIT.txt`).
- winget manifest: `License: MIT`, `LicenseUrl` pointing to `LICENSE`.
- Python source files carry `SPDX-License-Identifier: MIT` headers.
