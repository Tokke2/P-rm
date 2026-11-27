"""Tester för settings-självdiagnos + atomisk sparning (#9, v1.8.0).

settings.json kontrolleras vid start; korrupt fil repareras från intern
backup (.bak) som uppdateras vid VARJE lyckad sparning.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Script import settings_store  # noqa: E402


class SettingsDiagnosTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "settings.json"
        self.bak = Path(self.tmp.name) / "settings.json.bak"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_missing_file_creates_defaults(self) -> None:
        self.assertFalse(settings_store.diagnose_settings(self.path, self.bak))
        self.assertTrue(self.path.is_file())
        settings = settings_store.load_settings(self.path)
        self.assertEqual(settings["gui_language"], "sv")
        self.assertEqual(settings["minimize_to_tray"], False)
        self.assertEqual(settings["separate_row_pdfs"], False)

    def test_valid_file_refreshes_backup(self) -> None:
        self.path.write_text('{"text_size": 22}', encoding="utf-8")
        self.assertFalse(settings_store.diagnose_settings(self.path, self.bak))
        self.assertIn("text_size", self.bak.read_text(encoding="utf-8"))

    def test_corrupt_file_repaired_from_backup(self) -> None:
        self.path.write_text('{"text_size": 22}', encoding="utf-8")
        settings_store.diagnose_settings(self.path, self.bak)
        self.path.write_text("{OGILTIG JSON", encoding="utf-8")
        self.assertTrue(settings_store.diagnose_settings(self.path, self.bak))
        repaired = settings_store.load_settings(self.path)
        self.assertEqual(repaired["text_size"], 22)

    def test_corrupt_without_backup_falls_back_to_defaults(self) -> None:
        self.path.write_text("{OGILTIG JSON", encoding="utf-8")
        self.assertTrue(settings_store.diagnose_settings(self.path, self.bak))
        settings = settings_store.load_settings(self.path)
        self.assertEqual(settings["text_size"], 16)  # default

    def test_save_is_atomic_and_updates_backup(self) -> None:
        settings = dict(settings_store.DEFAULT_SETTINGS)
        settings["text_size"] = 30
        self.assertTrue(settings_store.save_settings(settings, self.path))
        self.assertFalse(self.path.with_suffix(".json.tmp").exists())
        self.assertIn("text_size", self.bak.read_text(encoding="utf-8"))
        self.assertEqual(settings_store.load_settings(self.path)["text_size"], 30)

    def test_non_dict_root_repaired(self) -> None:
        self.path.write_text('["lista", "inte", "objekt"]', encoding="utf-8")
        self.assertTrue(settings_store.diagnose_settings(self.path, self.bak))
        self.assertIn("label_type", self.path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
