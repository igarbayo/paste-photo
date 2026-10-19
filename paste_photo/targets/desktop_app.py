"""Aplicación oficial de escritorio de Claude (pendiente)."""

from paste_photo.targets._pending import register_pending

register_pending(
    "desktop_app",
    "Localizar la ventana de la app de Claude, abrir la pestaña Code y pegar con Ctrl+V / Cmd+V.",
)
