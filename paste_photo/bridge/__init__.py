# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Puente con la extensión del navegador.

    servicio (BridgeServer) ⇄ socket local ⇄ paste-photo-native-host ⇄ extensión

El navegador lanza `paste-photo-native-host` (native messaging) cuando la extensión se
conecta; el host reenvía mensajes entre la extensión y el servicio por un canal local
autenticado. Ver `paste_photo/bridge/CLAUDE.md`.
"""
