"""Automatiska tester för verifikatlogik, PDF-ritning och logotypimport.

Kör: python -m unittest discover -s tests -v
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image  # noqa: E402
from pypdf import PdfReader  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.pdfgen import canvas  # noqa: E402

from Script import label, logotyp, settings_store, ui_layout, verifikat  # noqa: E402


class VerifikatTests(unittest.TestCase):
    def test_whole_year_counts(self) -> None:
        for per_month, expected in ((1, 12), (2, 24), (3, 36), (12, 144)):
            texts = verifikat.build_verifikat_texts(2026, per_month)
            self.assertEqual(len(texts), expected)

    def test_order_is_month_then_number(self) -> None:
        texts = verifikat.build_verifikat_texts(2026, 2)
        self.assertEqual(texts[0], "VERIFIKAT\nJAN\n1\n2026")
        self.assertEqual(texts[1], "VERIFIKAT\nJAN\n2\n2026")
        self.assertEqual(texts[2], "VERIFIKAT\nFEB\n1\n2026")
        self.assertEqual(texts[-1], "VERIFIKAT\nDEC\n2\n2026")

    def test_filenames_separate_the_two_variants(self) -> None:
        one = verifikat.verifikat_filename(2026, 1)
        two = verifikat.verifikat_filename(2026, 2)
        self.assertEqual(one, "verifikat_2026_1_per_manad.pdf")
        self.assertEqual(two, "verifikat_2026_2_per_manad.pdf")
        self.assertNotEqual(one, two)

    def test_invalid_input_raises(self) -> None:
        with self.assertRaises(ValueError):
            verifikat.build_verifikat_texts(2026, 0)
        with self.assertRaises(ValueError):
            verifikat.build_verifikat_texts(1800, 2)
        with self.assertRaises(ValueError):
            verifikat.build_verifikat_texts("abc", 2)

    def test_pagination_and_order_with_fake_canvas(self) -> None:
        class FakeCanvas:
            def __init__(self) -> None:
                self.pages = 1

            def showPage(self) -> None:  # noqa: N802 (reportlab-API)
                self.pages += 1

        placed = []
        pages_started = []

        def draw_label(pdf, x, y, width, height, text) -> None:
            placed.append((pdf.pages, text, x, y))

        fake = FakeCanvas()
        texts = verifikat.build_verifikat_texts(2030, 2)
        pages = verifikat.draw_verifikat_labels(
            fake, texts, 41 * mm, 64 * mm, draw_label,
            lambda cols, rows: pages_started.append((cols, rows)),
        )
        self.assertEqual(pages, 2)
        self.assertEqual(fake.pages, 2)
        self.assertEqual(len(placed), 24)
        self.assertEqual(len(pages_started), 2)
        self.assertEqual(placed[0][1], texts[0])
        self.assertEqual(placed[-1][1], texts[-1])
        self.assertEqual(placed[0][0], 1)
        self.assertEqual(placed[-1][0], 2)
        # Ingen etikett får hamna utanför A4:ans nedre kant.
        self.assertTrue(all(y >= 0 for _, _, _, y in placed))

    def test_pdf_can_be_rendered_and_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "verifikat_2026_2_per_manad.pdf"
            pdf = canvas.Canvas(str(out), pagesize=A4, pageCompression=1)
            texts = verifikat.build_verifikat_texts(2026, 2)
            for index, text in enumerate(texts):
                if index and index % 12 == 0:
                    pdf.showPage()
                label.draw_single_label(
                    pdf, 10 * mm, 10 * mm, 41 * mm, 64 * mm, text,
                    initial_font_size=16,
                )
            pdf.save()

            reader = PdfReader(str(out))
            self.assertGreaterEqual(len(reader.pages), 2)
            all_text = "\n".join(page.extract_text() or "" for page in reader.pages)
            self.assertIn("VERIFIKAT", all_text)
            self.assertIn("JAN", all_text)
            self.assertIn("DEC", all_text)
            self.assertIn("2026", all_text)


class LogoTests(unittest.TestCase):
    def test_png_logo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "logo.png"
            Image.new("RGBA", (1200, 400), (200, 30, 30, 255)).save(source)
            image = logotyp.load_and_resize_logo(str(source), max_width_mm=40)
            self.assertIsNotNone(image)
            self.assertEqual(image.width, round(40 * logotyp.DPI / 25.4))
            self.assertAlmostEqual(image.height / image.width, 400 / 1200, delta=0.02)

    def test_small_raster_is_not_artificially_upscaled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "small-logo.png"
            Image.new("RGBA", (300, 150), (20, 90, 180, 255)).save(source)
            image = logotyp.load_and_resize_logo(str(source), max_width_mm=40)
            self.assertIsNotNone(image)
            self.assertEqual(image.width, 300)

    @unittest.skipUnless(logotyp._pymupdf_module(), "PyMuPDF är inte installerat")
    def test_pdf_logo_uses_first_page(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "logo.pdf"
            pdf = canvas.Canvas(str(source), pagesize=(200, 100))
            pdf.setFillColorRGB(0.9, 0.1, 0.1)
            pdf.rect(20, 20, 100, 60, fill=1)
            pdf.showPage()
            pdf.rect(0, 0, 10, 10, fill=1)
            pdf.save()

            image = logotyp.load_and_resize_logo(str(source), max_width_mm=40)
            self.assertIsNotNone(image)
            self.assertEqual(image.mode, "RGBA")
            self.assertGreater(image.width, 400)
            self.assertLessEqual(image.width, round(40 * logotyp.DPI / 25.4))
            self.assertLess(image.height, image.width)

    @unittest.skipUnless(
        logotyp._cairosvg_module() or logotyp._pymupdf_module(),
        "Ingen SVG-konverterare installerad",
    )
    def test_svg_logo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "logo.svg"
            source.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" '
                'width="200" height="100"><rect width="200" height="100" '
                'fill="#cc2222"/></svg>',
                encoding="utf-8",
            )
            image = logotyp.load_and_resize_logo(str(source), max_width_mm=40)
            self.assertIsNotNone(image)
            self.assertEqual(image.width, round(40 * logotyp.DPI / 25.4))

    def test_missing_file_returns_none(self) -> None:
        self.assertIsNone(logotyp.load_and_resize_logo("/does/not/exist.pdf"))


class ResponsiveLayoutTests(unittest.TestCase):
    def test_window_fits_small_screen(self) -> None:
        geometry, min_width, min_height = ui_layout.compute_window_geometry(
            800, 600, "1200x900+50+30"
        )
        self.assertEqual(geometry, "768x540+16+0")
        self.assertEqual(min_width, 680)
        self.assertEqual(min_height, 420)

    def test_window_uses_max_height_and_saved_width_when_possible(self) -> None:
        geometry, min_width, min_height = ui_layout.compute_window_geometry(
            1920, 1080, "900x500+30+30"
        )
        self.assertEqual(geometry, "900x1020+510+0")
        self.assertEqual(min_width, 680)
        self.assertEqual(min_height, 420)

    def test_saved_width_is_clamped_to_screen(self) -> None:
        geometry, _, _ = ui_layout.compute_window_geometry(1024, 768, "1800x700")
        self.assertEqual(geometry, "992x708+16+0")


class SettingsTests(unittest.TestCase):
    def test_roundtrip_and_corrupt_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            data = settings_store.load_settings(path)
            self.assertEqual(data["verifikat_per_month"], 2)
            data["verifikat_year"] = 2030
            data["verifikat_per_month"] = 1
            self.assertTrue(settings_store.save_settings(data, path))
            loaded = settings_store.load_settings(path)
            self.assertEqual(loaded["verifikat_year"], 2030)
            self.assertEqual(loaded["verifikat_per_month"], 1)

            path.write_text("{inte json", encoding="utf-8")
            loaded = settings_store.load_settings(path)
            self.assertEqual(loaded, settings_store.DEFAULT_SETTINGS)


if __name__ == "__main__":
    unittest.main()
