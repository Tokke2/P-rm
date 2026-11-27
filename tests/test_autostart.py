"""Tester för autostart (§9: pythonw, ingen terminal) + no-console-skydd.

Autostart-logiken testas med FAKE-winreg (helt offline, ingen riktig
registry). Kör: python -m unittest discover -s tests -v
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Script import autostart, skarm  # noqa: E402


class _FakeKey:
    """Låter kontexthanteraren fungera som en riktig registreringsnyckel."""

    def __init__(self, store: dict) -> None:
        self.store = store

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        return None

    def SetValueEx(self, value_name, _reserved, _type, value) -> None:
        self.store[value_name] = value

    def QueryValueEx(self, key_name):
        if key_name not in self.store:
            raise FileNotFoundError(key_name)
        return self.store[key_name], None

    def DeleteValue(self, key_name) -> None:
        if key_name not in self.store:
            raise FileNotFoundError(key_name)
        del self.store[key_name]


class _FakeWinreg(SimpleNamespace):
    """Minimal fake av winreg-API:t som autostart-modulen använder."""

    HKEY_CURRENT_USER = "HKCU"
    KEY_SET_VALUE = "write"
    KEY_READ = "read"
    REG_SZ = "str"

    def __init__(self) -> None:
        super().__init__(store={})

    def OpenKey(self, _root, _path, _reserved, access):
        return _FakeKey(self.store)


class AutostartTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fake = _FakeWinreg()

    def test_build_autostart_command_prefers_pythonw(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pythonw = Path(tmp) / "pythonw.exe"
            pythonw.write_text("", encoding="utf-8")
            python = Path(tmp) / "python.exe"
            python.write_text("", encoding="utf-8")
            command = autostart.build_autostart_command(str(python), "app.py")
            self.assertIn("pythonw.exe", command)
            self.assertIn('"app.py"', command)
            self.assertTrue(command.startswith('"'))

    def test_build_autostart_command_falls_back(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            python = Path(tmp) / "python.exe"
            python.write_text("", encoding="utf-8")
            command = autostart.build_autostart_command(str(python), "app.py")
            self.assertIn("python.exe", command)

    def test_enable_write_and_read(self) -> None:
        self.assertFalse(autostart.is_autostart_enabled(self.fake))
        self.assertTrue(autostart.enable_autostart(
            script_path="C:\\App\\folder_qt.py",
            python_exe="C:\\Py\\python.exe",
            winreg_module=self.fake,
        ))
        self.assertTrue(autostart.is_autostart_enabled(self.fake))
        command = autostart.get_autostart_command(self.fake)
        self.assertIn("folder_qt.py", command)
        self.assertIn('"C:\\App\\folder_qt.py"', command)

    def test_disable_removes_value(self) -> None:
        autostart.enable_autostart(
            script_path="x.py", winreg_module=self.fake
        )
        self.assertTrue(autostart.disable_autostart(self.fake))
        self.assertFalse(autostart.is_autostart_enabled(self.fake))
        # Disable igen (redan borta) → fortfarande True.
        self.assertTrue(autostart.disable_autostart(self.fake))

    def test_non_windows_graceful_noop(self) -> None:
        # Utan winreg-modul: no-op False utan crash (sandboxen = Linux).
        self.assertFalse(autostart.enable_autostart(winreg_module=None))
        self.assertFalse(autostart.disable_autostart(winreg_module=None))
        self.assertFalse(autostart.is_autostart_enabled(winreg_module=None))
        self.assertIsNone(autostart.get_autostart_command(winreg_module=None))


class NoConsoleTests(unittest.TestCase):
    """§9: pythonw har sys.stdout = None — skyddet dirigerar till devnull."""

    def test_ensure_no_console_streams_redirects_none(self) -> None:
        import io

        original_out, original_err = sys.stdout, sys.stderr
        try:
            sys.stdout = None
            sys.stderr = None
            redirected = skarm.ensure_no_console_streams()
            self.assertTrue(redirected)
            self.assertIsNotNone(sys.stdout)
            self.assertIsNotNone(sys.stderr)
            # Print ska fungera utan konsol (inte krascha som förut):
            print("test utan konsol ✓")
            sys.stdout.flush()
        finally:
            sys.stdout, sys.stderr = original_out, original_err

    def test_ensure_no_console_streams_noop_with_streams(self) -> None:
        redirected = skarm.ensure_no_console_streams()
        self.assertFalse(redirected)  # sandboxen HAR strömmar


class FolderPyBootstrapTests(unittest.TestCase):
    """folder.py + folder_qt.py ska skydda print före allt annat (§9)."""

    def test_both_mains_call_guard_first(self) -> None:
        for name in ("folder.py", "folder_qt.py"):
            source = (Path(__file__).resolve().parent.parent / name).read_text(
                encoding="utf-8"
            )
            self.assertIn(
                "ensure_no_console_streams()", source,
                f"{name} saknar pythonw-skydd",
            )


if __name__ == "__main__":
    unittest.main()
