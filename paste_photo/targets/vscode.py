# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Extensión de Claude Code en VS Code (pendiente)."""

from paste_photo.targets._pending import register_pending

register_pending(
    "vscode",
    "Localizar la ventana de VS Code, enfocar el panel de Claude Code y pegar con Ctrl+V / Cmd+V.",
)
