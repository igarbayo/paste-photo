# Contributing to paste-photo

Thank you so much for taking the time to read this. It genuinely means a lot. paste-photo
is a small project with a single maintainer, and the fact that you are here considering
contributing to it is something we do not take for granted.

## Review times

There is no fixed deadline. Pull requests and issues are usually reviewed within **one to
two weeks**, but it can take longer. Thanks for your patience.

## Set up the environment

You need Python 3.11 or newer, Git and, to try it for real, Windows with Windows Terminal or
Chrome/Edge.

1. Fork the repository on GitHub and clone your fork:
   ```bash
   git clone https://github.com/<your-user>/paste-photo.git
   cd paste-photo
   ```
2. Create a virtual environment and install the project with its development tools:
   ```bash
   python -m venv .venv
   .venv\Scripts\python -m pip install -e ".[dev]"     # on macOS/Linux: .venv/bin/python
   ```
   Add `build` to the extras (`".[dev,build]"`) if you want to build the `.exe` with
   `python packaging/build.py`.
3. Check that everything is green before you change anything:
   ```bash
   .venv\Scripts\python -m pytest -q
   .venv\Scripts\ruff check .
   ```

## Make your change

1. Create a branch with a descriptive name, such as `feat/firefox-target` or
   `fix/wsl-timeout`:
   ```bash
   git switch -c fix/wsl-timeout
   ```
2. Make your change. Read [`CLAUDE.md`](CLAUDE.md) first: it explains the architecture and
   where each kind of change goes. For example, a new place where Claude can run is a new
   module in `paste_photo/targets/`, and a new operating system is a new folder in
   `paste_photo/platforms/`.
3. Add or update tests in `tests/`. The core is tested with the fakes in `tests/fakes.py`,
   so the tests run on any operating system.
4. Add an entry under `## [Unreleased]` in [`CHANGELOG.md`](CHANGELOG.md), in the right
   category (`Added`, `Changed`, `Fixed`...).
5. Run a clean build: tests and lint must pass.
6. Push your branch and open a pull request against `main`. Explain what you changed, why,
   and how you tested it.

At least one maintainer must approve the pull request before it is merged.

## Licensing of contributions

paste-photo is licensed under the [MIT License](LICENSE). By opening a pull request you agree
that your contribution is released under that same license. New Python files start with:

```python
# SPDX-FileCopyrightText: 2026 <your name>
# SPDX-License-Identifier: MIT
```

If your change adds a dependency, check its license first. Permissive licenses and LGPL are
fine; GPL or AGPL are not accepted without discussing it in an issue, because they would
change the license of the installer. See
[docs/COMPONENTS_LICENSE.md](docs/COMPONENTS_LICENSE.md#5-adding-or-updating-a-dependency).

## Coding standards

- Style is [PEP 8](https://peps.python.org/pep-0008/), enforced by **ruff** as configured in
  `pyproject.toml` (line length 100, rules `E`, `F`, `I`, `UP` and `B`). Run
  `ruff check --fix .` to fix most issues automatically.
- Use type hints everywhere, and `typing.Protocol` for interfaces.
- Use `logging` instead of `print`.
- `paste_photo/core/` must never import anything specific to an operating system.

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```text
<type>(<optional scope>): <short summary>

<optional body: what and why>
```

The common types are `feat`, `fix`, `docs`, `test`, `refactor` and `chore`. Some examples:

```text
feat(browser): detect Claude tabs in Firefox
fix(windows): do not paste the same image twice
docs: explain WSL support in the README
```

## Definition of done

A contribution is ready to merge when:

- [ ] `pytest` and `ruff check .` pass.
- [ ] New behavior is covered by tests.
- [ ] `CHANGELOG.md` has an entry under `[Unreleased]`.
- [ ] The README describes the product as it is after your change (new or changed
      features, options, platforms).
- [ ] User-facing options are documented in `paste_photo/resources/default_config.toml`.
- [ ] New files carry the SPDX header, and new dependencies have a compatible license.
- [ ] Commits follow Conventional Commits.
- [ ] A maintainer has approved the pull request.

## Questions

Open an [issue](https://github.com/igarbayo/paste-photo/issues) or mention the maintainer,
[@igarbayo](https://github.com/igarbayo).
