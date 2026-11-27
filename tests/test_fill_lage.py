"""Tester för fyll-läget (v1.10.0): texten fyller alltid etiketten med
5 px marginal och delas ALDRIG upp på flera rader + Inställningar-flik +
Tjock rygg som standard."""

from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Script import label  # noqa: E402
from Script import settings_store  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
QT_SOURCE = (ROOT / "folder.py").read_text(encoding="utf-8")


def _make_canvas():
    from reportlab.pdfgen import canvas as rl_canvas
    return rl_canvas.Canvas(io.BytesIO(), pagesize=(400, 400))


class FillLageTests(unittest.TestCase):
    """_fit_single_line: exakt matematik för fyll-läget."""

    def setUp(self) -> None:
        self.c = _make_canvas()
        self.font = "Helvetica-Bold"
        self.text = "REDOVISNING 2025"

    def test_width_binds_for_long_text(self) -> None:
        # 100 pt tillgänglig bredd → storlek så att bredden blir exakt 100.
        size = label._fit_single_line(self.c, self.text, self.font, 100.0, 500.0)
        width = self.c.stringWidth(self.text, self.font, size)
        self.assertAlmostEqual(width, 100.0, places=6)

    def test_height_binds_for_short_text(self) -> None:
        # Kort text + liten höjd → storleken begränsas av höjden.
        size = label._fit_single_line(self.c, "A", self.font, 500.0, 80.0, 1.0)
        self.assertAlmostEqual(size, 80.0, places=6)
        # Med radavstånd 1.2 → höjd/1.2
        size2 = label._fit_single_line(self.c, "A", self.font, 500.0, 80.0, 1.2)
        self.assertAlmostEqual(size2, 80.0 / 1.2, places=6)

    def test_margin_gives_5px_from_edges(self) -> None:
        # Anroparen drar av 2×5 px: 41 mm-bredd − 10 pt breddmarginal.
        width = 41 * 2.834645669  # mm→pt
        avail = width - 2 * label.FILL_TEXT_MARGIN_PT
        size = label._fit_single_line(self.c, self.text, self.font, avail, 500.0)
        drawn = self.c.stringWidth(self.text, self.font, size)
        self.assertAlmostEqual(drawn, avail, places=6)
        self.assertEqual(label.FILL_TEXT_MARGIN_PT, 5.0)

    def test_never_exceeds_cap(self) -> None:
        size = label._fit_single_line(self.c, "A", self.font, 10_000.0, 10_000.0)
        self.assertEqual(size, label.FILL_MAX_FONT_PT)

    def test_empty_text_is_safe(self) -> None:
        self.assertEqual(label._fit_single_line(self.c, "", self.font, 100, 100), 1.0)
        self.assertEqual(label._fit_single_line(self.c, "  ", self.font, 100, 100), 1.0)

    def test_draw_never_wraps_in_fill_mode(self) -> None:
        """fill_text=True anropar ALDRIG radbrytaren (dela aldrig upp)."""
        calls = []
        original = label._break_text_into_lines
        label._break_text_into_lines = lambda *a, **k: calls.append(a)
        try:
            label.draw_single_label(
                self.c, 50, 50, 41 * 2.834645669, 64 * 2.834645669,
                "EN JÄTTELÅNG TEXT SOM ALDRIG FÅR BRYTAS",
                fill_text=True,
            )
        finally:
            label._break_text_into_lines = original
        self.assertEqual(calls, [], "fill-läget fick inte bryta rader")


class InställningarFlikTests(unittest.TestCase):
    """Ny flik + Tjock rygg som standard."""

    def test_settings_tab_exists_and_registered(self) -> None:
        self.assertIn("def _build_settings_tab", QT_SOURCE)
        self.assertIn('self.tabs.addTab(self.settings_tab, "Inställningar")', QT_SOURCE)
        self.assertIn("self._build_settings_tab()", QT_SOURCE)

    def test_all_widgets_moved_to_settings_tab(self) -> None:
        for name in (
            "multi_label_check", "cut_lines_check", "corner_marks_check",
            "barcode_check", "logo_contrast_check", "antal_spin",
            "auto_update_checkbox", "autostart_checkbox", "tray_checkbox",
            "separate_rows_check",
        ):
            self.assertIn(f"self.{name}", QT_SOURCE)
        # Gamla vänsterpanel-widgetar borttagna:
        self.assertNotIn("text_size_spin", QT_SOURCE)
        self.assertNotIn("auto_shrink_check", QT_SOURCE)

    def test_tjock_rygg_is_default(self) -> None:
        self.assertEqual(
            settings_store.DEFAULT_SETTINGS["label_type"], "rygg_tjock"
        )
        self.assertIn('self.saved.get("label_type", "rygg_tjock")', QT_SOURCE)
        self.assertIn('return "rygg_tjock"', QT_SOURCE)

    def test_all_draw_calls_use_fill_mode(self) -> None:
        self.assertEqual(QT_SOURCE.count("fill_text=True"), 3)
        self.assertNotIn("auto_shrink_text=", QT_SOURCE)

    def test_fill_info_text_visible(self) -> None:
        self.assertIn(
            "fyller etiketten", QT_SOURCE
        )


if __name__ == "__main__":
    unittest.main()
