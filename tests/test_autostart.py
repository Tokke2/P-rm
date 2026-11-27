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
    """PyHKEY-liknande: bara kontexthantering (Close/Detach-liknande).

    VIKTIGT: det RIKTIGA winreg.PyHKEY-objektet har INTE SetValueEx/
    QueryValueEx/DeleteValue — de finns på modulnivå. Faken speglar det.
    """

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        return None


class _FakeWinreg(SimpleNamespace):
    """Fake av winreg-MODULEN (modulnivå-funktioner med nyckel först)."""

    HKEY_CURRENT_USER = "HKCU"
    KEY_SET_VALUE = "write"
    KEY_READ = "read"
    REG_SZ = "str"

    def __init__(self) -> None:
        super().__init__(store={}, _open=False)

    def OpenKey(self, _root, _path, _reserved, access):
        self._open = True
        return _FakeKey()

    def SetValueEx(self, _key, value_name, _reserved, _type, value) -> None:
        self.store[value_name] = value

    def QueryValueEx(self, _key, value_name):
        if value_name not in self.store:
            raise FileNotFoundError(value_name)
        return self.store[value_name], None

    def DeleteValue(self, _key, value_name) -> None:
        if value_name not in self.store:
            raise FileNotFoundError(value_name)
        del self.store[value_name]


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
    """folder.py (Qt) ska skydda print före allt annat (§9);
    folder_qt.py är den kompatibla startaren som anropar folder.main()."""

    def test_folder_py_calls_guard_first(self) -> None:
        source = (Path(__file__).resolve().parent.parent / "folder.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("ensure_no_console_streams()", source)
        self.assertLess(
            source.find("ensure_no_console_streams()"),
            source.find("from Script import ("),
        )

    def test_folder_qt_launcher_imports_folder(self) -> None:
        source = (Path(__file__).resolve().parent.parent / "folder_qt.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("from folder import main", source)

    def test_autostart_default_targets_folder_py(self) -> None:
        command = autostart.build_autostart_command(
            python_exe="C:\\Py\\python.exe", script_path=None
        )
        self.assertIn("folder.py", command)


class WinregApiRegressionTests(unittest.TestCase):
    """P0-regression v1.7.1: riktigt winreg-API — PyHKEY-objektet har bara
    Close/Detach; värdefunktionerna (SetValueEx/QueryValueEx/DeleteValue)
    finns på MODULE-nivå med nyckeln som första argument.

    v1.7.0 kraschade på Windows: autostart kallade key.QueryValueEx(...)
    → AttributeError i GUI-starten. Dessa tester simulerar det RIKTIGA
    winreg-API:t och ett udda API (försvarslag: no-op, aldrig crash).
    """

    def _riktig_winreg_lik(self):
        """Fake som speglar riktigt winreg: modulnivå + PyHKEY utan metoder."""

        class PyHKEYLiknande:  # exakt som riktigt winreg.PyHKEY
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def Close(self):
                pass

            def Detach(self):
                return 1

        fake = SimpleNamespace(
            HKEY_CURRENT_USER="HKCU", KEY_SET_VALUE="w",
            KEY_READ="r", REG_SZ="str", store={},
        )

        def open_key(_root, _path, _reserved, _access):
            return PyHKEYLiknande()

        def set_value_ex(_key, value_name, _reserved, _type, value):
            fake.store[value_name] = value

        def query_value_ex(_key, value_name):
            if value_name not in fake.store:
                raise FileNotFoundError(value_name)
            return fake.store[value_name], None

        def delete_value(_key, value_name):
            if value_name not in fake.store:
                raise FileNotFoundError(value_name)
            del fake.store[value_name]

        fake.OpenKey = open_key
        fake.SetValueEx = set_value_ex
        fake.QueryValueEx = query_value_ex
        fake.DeleteValue = delete_value
        return fake

    def test_module_level_api_roundtrip(self) -> None:
        fake = self._riktig_winreg_lik()
        self.assertTrue(autostart.enable_autostart(
            script_path="C:\\App\\folder.py",
            python_exe="C:\\Py\\python.exe",
            winreg_module=fake,
        ))
        self.assertTrue(autostart.is_autostart_enabled(fake))
        self.assertIn("folder.py", autostart.get_autostart_command(fake))
        self.assertTrue(autostart.disable_autostart(fake))
        self.assertFalse(autostart.is_autostart_enabled(fake))

    def test_pyhkey_without_value_methods_is_used(self) -> None:
        """Nyckelobjektet UTAN värdefunktioner (som riktigt PyHKEY) fungerar."""
        fake = self._riktig_winreg_lik()
        key = fake.OpenKey(fake.HKEY_CURRENT_USER, "x", 0, fake.KEY_READ)
        self.assertFalse(hasattr(key, "QueryValueEx"))  # guard på faken självt

    def test_odd_winreg_never_crashes(self) -> None:
        """Udda winreg-implementation → no-op; appen startar ändå (§9)."""

        class Tom(SimpleNamespace):
            HKEY_CURRENT_USER = "HKCU"
            KEY_SET_VALUE = "w"
            KEY_READ = "r"
            REG_SZ = "str"

            def OpenKey(self, *args):
                return SimpleNamespace(__enter__=lambda s: s, __exit__=lambda s, *a: None)

        tom = Tom()
        self.assertFalse(autostart.enable_autostart(winreg_module=tom))
        self.assertFalse(autostart.is_autostart_enabled(winreg_module=tom))
        self.assertFalse(autostart.disable_autostart(winreg_module=tom))
        self.assertIsNone(autostart.get_autostart_command(winreg_module=tom))


if __name__ == "__main__":
    unittest.main()
