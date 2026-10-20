# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Regex del destino browser contra nombres de pestaña y URLs reales de Chrome/Edge."""

import re

import pytest

from paste_photo.targets.browser import DEFAULT_TITLE_REGEX, DEFAULT_URL_REGEX
from paste_photo.targets.windows_terminal import DEFAULT_TITLE_REGEX as WT_TITLE_REGEX

TITLE = re.compile(DEFAULT_TITLE_REGEX)
URL = re.compile(DEFAULT_URL_REGEX, re.IGNORECASE)


@pytest.mark.parametrize(
    "name",
    [
        "Claude",
        "Nuevo chat - Claude",
        "Design - Claude",
        "Claude Code",
        "Claude Code: parte del grupo ⌛Claude",
        "Uso de memoria de Claude Code: parte del grupo ✅Claude: 613 MB",
        "Uso de memoria de Explicación rápida de funciones - Claude: 345 MB",
        "Chat nuevo - Claude - Uso de memoria - 353 MB",
        "Claude Design",
        "Nuevo chat - Claude — Mozilla Firefox",  # títulos de ventana en Linux
        "Nuevo chat - Claude - Chromium",
    ],
)
def test_title_matches_claude_tabs(name):
    assert TITLE.search(name)


@pytest.mark.parametrize(
    "name",
    [
        "Claude Code overview - Claude Docs",
        "Uso de memoria de Tu enlace seguro a Claude está aquí | 2026 - Gmail: 385 MB",
        "Uso de memoria de 2026-09-16 Compleja Seminario.pdf: 145 MB",
        "Anthropic Claude-3 paper.pdf",
        "ClaudeBot",
    ],
)
def test_title_ignores_other_tabs(name):
    assert not TITLE.search(name)


@pytest.mark.parametrize(
    "url",
    [
        "https://claude.ai/new",
        "claude.ai/code/session_011irnzLnUSxrGiKtqmR11zr",
        "https://claude.ai/design/p/e6bfc416?file=x.html",
        "https://claude.ai",
    ],
)
def test_url_matches_claude(url):
    assert URL.search(url)


@pytest.mark.parametrize(
    "url",
    ["https://claude.ai.evil.com/", "https://example.com/?q=claude.ai", "C:/Users/doc.pdf"],
)
def test_url_ignores_others(url):
    assert not URL.search(url)


def test_windows_terminal_title():
    wt = re.compile(WT_TITLE_REGEX)
    assert wt.search("◑ paste-photo-windows-terminal")
    assert wt.search("✳ Claude Code")
    assert not wt.search("PowerShell")
