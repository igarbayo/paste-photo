"""claude.ai/code en un navegador (pendiente)."""

from paste_photo.targets._pending import register_pending

register_pending(
    "browser",
    "Buscar la pestaña cuyo título/URL coincida con claude.ai/code (UI Automation o extensión) "
    "y pegar con Ctrl+V / Cmd+V en el editor.",
)
