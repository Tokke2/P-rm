"""Tester för logotypmotorn (v1.10.1): PyMuPDF är huvudväg — Inkscape är
ALDRIG ett krav; riktiga SVG-renderingar verifieras offline."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Script import logotyp  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
APP_SVG = ROOT / "assets" / "app_logotyp.svg"


class LogotypMotorTests(unittest.TestCase):
    def test_pymupdf_is_primary_in_svg_chain(self) -> None:
        """SVG-kedjan: PyMuPDF FÖRE cairosvg/Inkscape (Inkscape aldrig krav)."""
        source = (ROOT / "Script" / "logotyp.py").read_text(encoding="utf-8")
        idx_pymupdf = source.find("# 1) PyMuPDF — HUVUDVÄG")
        idx_cairo = source.find("# 2) cairosvg (valfritt extra)")
        idx_inkscape = source.find("# 3) Inkscape (valfritt extra — ALDRIG ett krav)")
        self.assertGreater(idx_pymupdf, 0)
        self.assertLess(idx_pymupdf, idx_cairo)
        self.assertLess(idx_cairo, idx_inkscape)
        self.assertIn("Inkscape är aldrig ett krav", source)

    def test_requirements_include_pymupdf(self) -> None:
        """§4: PyMuPDF deklarerat — logotyper fungerar efter pip install."""
        req = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        self.assertIn("PyMuPDF", req)

    def test_draw_errors_land_on_loggfliken(self) -> None:
        """Ritfel syns på Loggar-fliken (LOGO_DRAW), inte bara i konsolen."""
        label_src = (ROOT / "Script" / "label.py").read_text(encoding="utf-8")
        self.assertIn("LOGO_DRAW", label_src)
        self.assertIn("Logotypen kunde inte ritas", label_src)

    def test_help_says_no_external_requirements(self) -> None:
        folder_src = (ROOT / "folder.py").read_text(encoding="utf-8")
        self.assertIn("inga externa verktyg", folder_src)
        self.assertIn("Inkscape är aldrig ett krav", folder_src)

    def test_real_svg_renders_with_pymupdf(self) -> None:
        """RIKTIG rendering: app-logotypen SVG → PNG med innehåll.

        Skippar om PyMuPDF saknas (alltid när requirements installerats).
        """
        mod = logotyp._pymupdf_module()
        if mod is None:
            self.skipTest("PyMuPDF saknas i miljön")
        self.assertTrue(APP_SVG.is_file())
        out = logotyp.convert_svg_to_png(str(APP_SVG), 400)
        self.assertIsNotNone(out)
        from PIL import Image
        img = Image.open(out).convert("RGBA")
        visible = sum(
            1 for value in img.getchannel("A").getdata() if value > 10
        )
        self.assertGreater(visible, 1000, "renderingen gav nästan tom bild")

    def test_logo_prepared_and_drawable(self) -> None:
        """SVG-logotypen förbereds och ritas in i en riktig PDF."""
        mod = logotyp._pymupdf_module()
        if mod is None:
            self.skipTest("PyMuPDF saknas i miljön")
        import io
        prepared = logotyp.load_and_resize_logo(str(APP_SVG))
        self.assertIsNotNone(prepared)
        from Script import label as label_module
        from reportlab.pdfgen import canvas as rl_canvas
        buffer = io.BytesIO()
        c = rl_canvas.Canvas(buffer, pagesize=(200, 200))
        label_module.draw_single_label(
            c, 10, 10, 120, 160, "TEST",
            prepared_logo_image=prepared, fill_text=True,
        )
        c.save()
        self.assertGreater(len(buffer.getvalue()), 1000)


if __name__ == "__main__":
    unittest.main()
