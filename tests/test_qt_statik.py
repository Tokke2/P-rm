"""Statisk Qt-audit (alltid körbar — även i miljöer utan PySide6).

folder.py är sedan v1.6.0 Qt-appen (tkinter ersatt) och kan inte
importeras här (PySide6 kräver libGL som sandboxen saknar) — därför
analyseras KÄLLKODEN med AST/strängsökning. På Windows körs dessutom
riktiga offscreen-Qt-tester.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QT_SOURCE = (ROOT / "folder.py").read_text(encoding="utf-8")
TREE = ast.parse(QT_SOURCE)
LAUNCHER_SOURCE = (ROOT / "folder_qt.py").read_text(encoding="utf-8")


class FolderQtStrukturTests(unittest.TestCase):
    """Qt-versionen ska spegla tkinter-versionens layout och funktioner."""

    def test_file_parses(self) -> None:
        self.assertTrue(TREE)

    def test_mainwindow_class_exists(self) -> None:
        classes = [
            node.name for node in ast.walk(TREE)
            if isinstance(node, ast.ClassDef)
        ]
        self.assertIn("MainWindow", classes)

    def test_same_tabs_as_tkinter_version(self) -> None:
        for text in ("Generator", "Hjälp", "Loggar"):
            self.assertIn(f'"{text}"', QT_SOURCE)

    def test_same_buttons_as_tkinter_version(self) -> None:
        for text in (
            "📄 SKAPA PDF",
            "🗂 Skapa arkivindex (A4, platskoder) (#1)",
            "⬇️ Sök uppdatering (REQ-K4)",
            "🕒 Auto-uppdatering 00:00 varje dag",
            "🚀 Autostart vid inloggning (utan terminal)",
            "⭐ Använd appens logotyp (vektor)",
            "🧾 Skapa BÅDA (1 & 2 per månad)",
        ):
            self.assertIn(text, QT_SOURCE, f"Saknad knapptext: {text}")

    def test_qss_uses_logotype_colors(self) -> None:
        # Logotypens djupblå + orange finns i QSS-designen.
        self.assertIn("#1E3A5F", QT_SOURCE)
        self.assertIn("#F6A03C", QT_SOURCE)

    def test_reuses_all_script_modules(self) -> None:
        for module in (
            "label", "logotyp", "settings_store", "verifikat",
            "arkivindex", "streckkod", "loggar", "skarm", "updater",
            "autostart",
        ):
            self.assertIn(f"{module} as", QT_SOURCE, f"Modulen {module} saknas")

    def test_core_gui_functions_exist(self) -> None:
        methods = [
            node.name for node in ast.walk(TREE)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        for name in (
            "create_pdf", "create_verifikat_pdf", "create_verifikat_both",
            "create_arkivindex_pdf", "_included_texts", "_barcode_text_for",
            "update_label_fields", "check_updates_clicked",
            "_schedule_auto_update", "_trigger_auto_update",
            "_on_autostart_toggled", "_refresh_loggar",
            "_clear_selected_errors", "choose_logo", "use_app_logo",
        ):
            self.assertIn(name, methods, f"Metoden {name} saknas")

    def test_no_terminal_window_helpers(self) -> None:
        # §9: pythonw-skydd FÖRST i modulen (innan andra imports används)
        # och CREATE_NO_WINDOW ligger i logotyp._run (skanning).
        self.assertLess(
            QT_SOURCE.find("ensure_no_console_streams()"),
            QT_SOURCE.find("from Script import ("),
        )
        logotyp_source = (ROOT / "Script" / "logotyp.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("CREATE_NO_WINDOW", logotyp_source)

    def test_start_geometry_uses_skarm_module(self) -> None:
        # §11: max höjd-läge via samma geometri-logik som tkinter-versionen
        self.assertIn("compute_start_geometry", QT_SOURCE)
        self.assertIn("availableGeometry", QT_SOURCE)

    def test_sorting_and_moving_table(self) -> None:
        # §10: inbyggd sortering + kolumnflyttning i Loggar-tabellen
        self.assertIn("setSortingEnabled(True)", QT_SOURCE)
        self.assertIn("setSectionsMovable(True)", QT_SOURCE)

    def test_autostart_uses_pythonw(self) -> None:
        autostart_source = (ROOT / "Script" / "autostart.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("pythonw.exe", autostart_source)
        self.assertIn("CurrentVersion\\Run", autostart_source)

    def test_settings_has_autostart_compatible_keys(self) -> None:
        # §4: ingen gamla nyckel borttagen; auto_update_daily finns i båda
        settings_source = (ROOT / "Script" / "settings_store.py").read_text(
            encoding="utf-8"
        )
        for key in (
            "auto_update_daily", "verifikat_period", "verifikat_language",
            "barcode_labels", "corner_marks", "logo_contrast", "label_type",
        ):
            self.assertIn(f'"{key}"', settings_source)

    def test_folder_py_is_qt_no_tkinter_left(self) -> None:
        """v1.6.0: tkinter är ERSATT — folder.py ska ha noll tkinter."""
        self.assertNotIn("import tkinter", QT_SOURCE)
        self.assertNotIn("ttkthemes", QT_SOURCE)
        self.assertIn("PySide6", QT_SOURCE)
        self.assertIn("QMainWindow", QT_SOURCE)

    def test_combobox_selection_wired(self) -> None:
        """Qt-sätt att binda val: currentTextChanged (inte ttk-signaler)."""
        self.assertGreaterEqual(QT_SOURCE.count("currentTextChanged"), 2)

    def test_launcher_keeps_old_paths_working(self) -> None:
        """folder_qt.py = kompatibel startare → folder.main() (gamla
        genvägar/autostart pekar dit)."""
        self.assertIn("from folder import main", LAUNCHER_SOURCE)
        self.assertIn("main()", LAUNCHER_SOURCE)

    def test_requirements_declare_pyside6(self) -> None:
        """§4: PySide6 deklarerat; tkinter-ttd-ttkthemes borttaget."""
        req = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        self.assertIn("PySide6", req)
        self.assertNotIn("ttkthemes", req)


if __name__ == "__main__":
    unittest.main()
