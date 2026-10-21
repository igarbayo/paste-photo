# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

"""Regex del destino browser contra nombres de pestaña y URLs reales de Chrome/Edge."""

import re

import pytest

from paste_photo.targets.browser import (
    DEFAULT_CHAT_URL_REGEX,
    DEFAULT_TITLE_REGEX,
    DEFAULT_URL_REGEX,
)
from paste_photo.targets.windows_terminal import DEFAULT_TITLE_REGEX as WT_TITLE_REGEX

TITLE = re.compile(DEFAULT_TITLE_REGEX)
URL = re.compile(DEFAULT_URL_REGEX, re.IGNORECASE)
CHAT = re.compile(DEFAULT_CHAT_URL_REGEX, re.IGNORECASE)


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


@pytest.mark.parametrize(
    "url",
    [
        "https://claude.ai",
        "https://claude.ai/",
        "https://claude.ai/new",
        "https://claude.ai/new?q=hola",
        "https://claude.ai/chat/0b1c2d3e",
        "https://claude.ai/chat/0b1c2d3e?ref=/artifact/x",  # "artifact" solo en la query
        "https://claude.ai/project/0b1c2d3e",
        "https://claude.ai/code",
        "claude.ai/code/session_011irnzLnUSxrGiKtqmR11zr",
        "https://claude.ai/design/p/e6bfc416?file=x.html",
    ],
)
def test_chat_url_accepts_prompt_pages(url):
    assert CHAT.search(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://claude.ai/artifact/0b1c2d3e",
        "https://claude.ai/code/artifact/0b1c2d3e",
        "https://claude.ai/artifacts",
        "https://claude.ai/code/artifacts",
        "https://claude.ai/public/artifacts/0b1c2d3e",
        "https://claude.ai/chat/0b1c2d3e/artifact/x",
        "https://claude.ai/share/0b1c2d3e",
        "https://claude.ai/recents",
        "https://claude.ai/projects",
        "https://claude.ai/settings/profile",
        "https://claude.ai/login",
        "https://claude.ai/upgrade",
        "https://claude.ai/newsletter",
        "https://claude.ai.evil.com/new",
    ],
)
def test_chat_url_rejects_other_claude_pages(url):
    assert not CHAT.search(url)


def test_windows_terminal_title():
    wt = re.compile(WT_TITLE_REGEX)
    assert wt.search("◑ paste-photo-windows-terminal")
    assert wt.search("✳ Claude Code")
    assert not wt.search("PowerShell")
