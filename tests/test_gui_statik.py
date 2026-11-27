"""Statisk GUI-audit — fångar ttk-optioner som inte finns (P0-regression v1.4.1).

v1.4.0 kraschade vid start på Windows: ttk.Combobox fick 'command='
(ttk har ingen sådan option — måste bindas via <<ComboboxSelected>>)
och ttk.Checkbutton fick 'width=' (även den ogiltig). Sandlådan saknar
tkinter, så dessa tester skannar KÄLLKODEN med AST istället och körs
alltid — på alla maskiner.
"""

from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

FOLDER_PY = Path(__file__).resolve().parent.parent / "folder.py"

# Ogiltiga keyword-argument per ttk-widget (källsökning i folder.py).
# OBS: ttk.Scrollbar och ttk.Scale HAR command (giltiga) — de ingår inte.
TTK_FORBIDDEN = {
    "Combobox": {"command"},          # bind <<ComboboxSelected>> i stället
    "Checkbutton": {"width"},         # använd padding/stil i stället
    "Notebook": {"command"},
    "Progressbar": {"command"},
    "Entry": {"command"},
}


def _calls_with_forbidden_keywords(source: str) -> list:
    """Returnerar [(widget, option, rad)] för ttk.X(... ogiltig=…)."""
    tree = ast.parse(source)
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Name)
                and func.value.id == "ttk"):
            continue
        forbidden = TTK_FORBIDDEN.get(func.attr)
        if not forbidden:
            continue
        for keyword in node.keywords:
            if keyword.arg in forbidden:
                violations.append(
                    (func.attr, keyword.arg, node.lineno)
                )
    return violations


class TtkOptionAuditTests(unittest.TestCase):
    """P0-regression: ttk-widgets ska aldrig få ogiltiga options."""

    def setUp(self) -> None:
        self.source = FOLDER_PY.read_text(encoding="utf-8")

    def test_no_forbidden_ttk_options(self) -> None:
        violations = _calls_with_forbidden_keywords(self.source)
        self.assertEqual(
            violations,
            [],
            f"ttk-widgets med ogiltiga options: {violations} "
            "(ttk = inga command=/width= — använd .bind(...) / padding)",
        )

    def test_combobox_selection_is_bound(self) -> None:
        """Komboboxarna ska binda <<ComboboxSelected>> (uppdatera info-raden)."""
        self.assertIn("<<ComboboxSelected>>", self.source)
        self.assertGreaterEqual(
            self.source.count("<<ComboboxSelected>>"), 2
        )  # period- + språk-komboboxen

    def test_audit_catches_the_original_bug(self) -> None:
        """Vakten ska själv hitta v1.4.0-buggen (sanity på testet självt)."""
        buggy = (
            "ttk.Combobox(master, values=('a',), command=self.x)\n"
            "ttk.Checkbutton(master, width=2)\n"
        )
        found = _calls_with_forbidden_keywords(buggy)
        self.assertEqual(found, [
            ("Combobox", "command", 1),
            ("Checkbutton", "width", 2),
        ])


if __name__ == "__main__":
    unittest.main()
