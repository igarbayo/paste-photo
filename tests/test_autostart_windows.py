import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="registro de Windows")

TEST_KEY = r"Software\paste-photo-tests\Run"


@pytest.fixture
def autostart():
    import winreg

    from paste_photo.platforms.windows.autostart import WindowsAutostart

    yield WindowsAutostart(key_path=TEST_KEY, value_name="paste-photo-test")
    for key in (TEST_KEY, r"Software\paste-photo-tests"):
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key)
        except FileNotFoundError:
            pass


def test_enable_disable_roundtrip(autostart):
    assert not autostart.is_enabled()
    autostart.enable('"C:\Apps\paste-photo.exe"')
    assert autostart.is_enabled()
    assert autostart.command() == '"C:\Apps\paste-photo.exe"'
    autostart.disable()
    assert not autostart.is_enabled()
    autostart.disable()  # idempotente
