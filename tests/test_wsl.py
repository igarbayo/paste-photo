# SPDX-FileCopyrightText: 2026 igarbayo
# SPDX-License-Identifier: MIT

import subprocess

import pytest

from paste_photo.targets import _wsl


@pytest.mark.parametrize(
    ("cmdline", "distro"),
    [
        (["C:\\Windows\\system32\\wsl.exe"], None),
        (["wsl.exe", "-d", "Ubuntu"], "Ubuntu"),
        (["wsl.exe", "~", "--distribution", "Debian"], "Debian"),
        (["wsl.exe", "--distribution=Ubuntu-24.04"], "Ubuntu-24.04"),
        (["wsl.exe", "-d"], None),
    ],
)
def test_distro_from_cmdline(cmdline, distro):
    assert _wsl.distro_from_cmdline(cmdline) == distro


def test_check_command_targets_distro():
    cmd = _wsl.check_command("Ubuntu")
    assert cmd[:3] == ["wsl.exe", "-d", "Ubuntu"]
    assert "[c]laude-code" in cmd[-1]  # no se encuentra a sí mismo con pgrep -f


def runner_returning(code):
    def run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, code)

    return run


def test_claude_running_results():
    assert _wsl.claude_running_in("U", runner=runner_returning(0)) is True
    assert _wsl.claude_running_in("U", runner=runner_returning(1)) is False
    assert _wsl.claude_running_in("U", runner=runner_returning(127)) is None


def test_claude_running_timeout_is_unknown():
    def run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, 3)

    assert _wsl.claude_running_in(None, runner=run) is None
