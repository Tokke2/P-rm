"""Tester för v1.1.0-funktionerna (förslag #1, #2, checkruta, #10, #11, #16, #22).

Kör: python -m unittest discover -s tests -v
"""

from __future__ import annotations

import importlib
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

from Script import arkivindex, label, logotyp, settings_store, verifikat  # noqa: E402
from Script import streckkod  # noqa: E402


class StreckkodTests(unittest.TestCase):
    """Code 128-B — verifierad mot Wikipedia/ISO-tabellen."""

    def test_known_anchor_patterns(self) -> None:
        # Externa ankarpunkter från specifikationstabellen:
        self.assertEqual(streckkod.CODE128_PATTERNS[33], "111323")   # 'A'
        self.assertEqual(streckkod.CODE128_PATTERNS[104], "211214")  # Start B
        self.assertEqual(streckkod.CODE128_PATTERNS[106], "233111")  # Stop
        self.assertEqual(
            streckkod.CODE128_PATTERNS[0], "212222"
        )  # värde 0 (space i B)

    def test_every_pattern_is_valid(self) -> None:
        for pattern in streckkod.CODE128_PATTERNS:
            self.assertEqual(len(pattern), 6)
            widths = [int(char) for char in pattern]
            self.assertEqual(sum(widths), 11)
            self.assertTrue(all(1 <= width <= 4 for width in widths))

    def test_modules_structure(self) -> None:
        modules = streckkod.code128_b_modules("ABC")
        # Start (11) + 3×11 + checksum (11) + stop (11 + 2) = 68 moduler.
        self.assertEqual(len(modules), streckkod.module_count("ABC"))
        self.assertEqual(streckkod.module_count("ABC"), 11 * 6 + 2)
        self.assertTrue(set(modules) <= {"0", "1"})
        self.assertTrue(modules.startswith("11010010000"))  # Start B binärt
        # Stop + slutbar: 1100011101011 (Wikipedia/ISO: 233111 + '2').
        self.assertTrue(modules.endswith("1100011101011"))

    def test_runs_alternate_and_sum_matches(self) -> None:
        runs = streckkod.code128_b_runs("Test 123")
        # Börjar och slutar med bar (stoppens slutbar) → udda antal runs.
        self.assertEqual(len(runs) % 2, 1)
        self.assertEqual(sum(runs), streckkod.module_count("Test 123"))
        for start_width in runs[::2]:
            self.assertGreaterEqual(start_width, 1)  # barer

    def test_checksum(self) -> None:
        # Handberäknad: Start B (104) + 1×'A'(33) = 137 mod 103 = 34.
        self.assertEqual(streckkod.code128_b_check_value("A"), 34)
        # Två tecken: 104 + 1×33 + 2×34 ('B'=34) = 205 mod 103 = 102.
        self.assertEqual(streckkod.code128_b_check_value("AB"), 102)

    def test_roundtrip_via_symbol_values(self) -> None:
        text = "Parm-A12"
        symbols = streckkod.code128_b_symbols(text)
        self.assertEqual(symbols[0], streckkod.START_B)
        self.assertEqual(symbols[-1], streckkod.STOP)
        data = symbols[1:-2]
        decoded = "".join(chr(value + streckkod.MIN_ASCII) for value in data)
        self.assertEqual(decoded, text)
        # Checksumman i symbolsekvensen ska motsvara beräknat värde.
        self.assertEqual(
            symbols[-2], streckkod.code128_b_check_value(text)
        )

    def test_invalid_text_raises(self) -> None:
        with self.assertRaises(ValueError):
            streckkod.code128_b_values("")
        with self.assertRaises(ValueError):
            streckkod.code128_b_values("häst")  # 'ä' utanför ASCII 32–126

    def test_draw_code128_renders_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "streck.pdf"
            pdf = canvas.Canvas(str(out), pagesize=A4)
            self.assertTrue(
                streckkod.draw_code128(pdf, 40 * mm, 200 * mm, 80 * mm, 12 * mm, "A1-01")
            )
            self.assertFalse(
                streckkod.draw_code128(pdf, 0, 0, 50, 10, "ogiltig ä ö")
            )
            pdf.save()
            reader = PdfReader(str(out))
            self.assertEqual(len(reader.pages), 1)


class ArkivindexTests(unittest.TestCase):
    """Förslag #1: smart arkivindex med platskoder."""

    def test_platskod_sequence(self) -> None:
        self.assertEqual(arkivindex.build_platskod(0), "A1-01")
        self.assertEqual(arkivindex.build_platskod(11), "A1-12")
        self.assertEqual(arkivindex.build_platskod(12), "A2-01")
        self.assertEqual(
            arkivindex.build_platskod(13, prefix="B", per_shelf=6), "B3-02"
        )
        with self.assertRaises(ValueError):
            arkivindex.build_platskod(-1)

    def test_entries_skip_empty_and_keep_order(self) -> None:
        entries = arkivindex.build_index_entries(
            ["Redovisning 2025", "", "HR-mappar", " "]
        )
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].platskod, "A1-01")
        self.assertEqual(entries[0].text, "Redovisning 2025")
        self.assertEqual(entries[1].platskod, "A1-02")
        self.assertEqual(entries[1].text, "HR-mappar")

    def test_pdf_renders_and_contains_platskoder(self) -> None:
        entries = arkivindex.build_index_entries(
            [f"Pärm {index}" for index in range(1, 41)]
        )
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "arkivindex.pdf"
            path = arkivindex.draw_arkivindex_pdf(out, entries)
            reader = PdfReader(str(path))
            self.assertGreaterEqual(len(reader.pages), 2)  # 40 rader → 2 sidor
            all_text = "\n".join(page.extract_text() or "" for page in reader.pages)
            self.assertIn("Arkivindex", all_text)
            self.assertIn("A1-01", all_text)
            self.assertIn("A2-05", all_text)  # rad 40

    def test_empty_entries_still_renders_header(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "tomt.pdf"
            path = arkivindex.draw_arkivindex_pdf(out, [])
            reader = PdfReader(str(path))
            self.assertEqual(len(reader.pages), 1)
            self.assertIn("Arkivindex", reader.pages[0].extract_text() or "")


class VerifikatPeriodOchSprakTests(unittest.TestCase):
    """Förslag #10 (kvartal/halvår) och #11 (flerspråkighet)."""

    def test_default_arguments_keep_old_behaviour(self) -> None:
        texts = verifikat.build_verifikat_texts(2026, 2)
        self.assertEqual(len(texts), 24)
        self.assertEqual(texts[0], "VERIFIKAT\nJAN\n1\n2026")
        self.assertEqual(texts[-1], "VERIFIKAT\nDEC\n2\n2026")
        self.assertEqual(
            verifikat.verifikat_filename(2026, 2),
            "verifikat_2026_2_per_manad.pdf",
        )

    def test_month_names_per_language(self) -> None:
        self.assertEqual(verifikat.month_names("se")[4], "MAJ")
        self.assertEqual(verifikat.month_names("en")[4], "MAY")
        self.assertEqual(verifikat.month_names("en")[9], "OCT")
        self.assertEqual(verifikat.month_names("no")[4], "MAI")
        self.assertEqual(verifikat.month_names("no")[11], "DES")
        with self.assertRaises(ValueError):
            verifikat.month_names("de")

    def test_kvartal_and_halvar(self) -> None:
        kvartal = verifikat.build_verifikat_texts(2026, 2, period="kvartal")
        self.assertEqual(len(kvartal), 8)
        self.assertEqual(kvartal[0], "VERIFIKAT\nQ1\n1\n2026")
        self.assertEqual(kvartal[1], "VERIFIKAT\nQ1\n2\n2026")
        self.assertEqual(kvartal[2], "VERIFIKAT\nQ2\n1\n2026")
        self.assertEqual(kvartal[-1], "VERIFIKAT\nQ4\n2\n2026")

        halvar = verifikat.build_verifikat_texts(2026, 3, period="halvar")
        self.assertEqual(len(halvar), 6)
        self.assertEqual(halvar[0], "VERIFIKAT\nH1\n1\n2026")
        self.assertEqual(halvar[3], "VERIFIKAT\nH2\n1\n2026")
        self.assertEqual(halvar[-1], "VERIFIKAT\nH2\n3\n2026")

    def test_kvartal_with_language_uses_months_only_for_manad(self) -> None:
        texts = verifikat.build_verifikat_texts(
            2027, 1, language="en", period="manad"
        )
        self.assertEqual(texts[0], "VERIFIKAT\nJAN\n1\n2027")
        self.assertIn("VERIFIKAT\nMAY\n1\n2027", texts)
        # Kvartal påverkas inte av språket.
        kv = verifikat.build_verifikat_texts(
            2027, 1, language="en", period="kvartal"
        )
        self.assertEqual(kv[0], "VERIFIKAT\nQ1\n1\n2027")

    def test_period_filenames(self) -> None:
        self.assertEqual(
            verifikat.verifikat_filename(2026, 2, period="kvartal"),
            "verifikat_2026_kvartal_2_per_kvartal.pdf",
        )
        self.assertEqual(
            verifikat.verifikat_filename(2026, 2, period="halvar"),
            "verifikat_2026_halvar_2_per_halvar.pdf",
        )

    def test_invalid_period_and_language_raise(self) -> None:
        with self.assertRaises(ValueError):
            verifikat.build_verifikat_texts(2026, 2, period="vecka")
        with self.assertRaises(ValueError):
            verifikat.build_verifikat_texts(2026, 2, language="fi")
        with self.assertRaises(ValueError):
            verifikat.verifikat_filename(2026, 2, period="decennium")


class LabelNyaFunktionerTests(unittest.TestCase):
    """Förslag #2 (streckkod), #16 (kontrast), #22 (hörnmarkeringar)."""

    def test_corner_mark_geometry(self) -> None:
        lines = label.corner_mark_lines(100.0, 60.0)
        self.assertEqual(len(lines), 8)  # 2 markeringar × 4 hörn
        for (x1, y1), (x2, y2) in lines:
            # Varje markering är L-formad: antingen horisontell eller vertikal.
            self.assertTrue(x1 == x2 or y1 == y2)
        self.assertTrue(label.corner_mark_lines(0, 0) == [])

    def test_luminance(self) -> None:
        black = Image.new("RGBA", (50, 20), (0, 0, 0, 255))
        white = Image.new("RGBA", (50, 20), (255, 255, 255, 255))
        transparent = Image.new("RGBA", (50, 20), (0, 0, 0, 0))
        self.assertAlmostEqual(logotyp.estimate_luminance(black), 0.0, places=2)
        self.assertAlmostEqual(logotyp.estimate_luminance(white), 1.0, places=2)
        # Helt transparent bild kompositeras mot vitt → vit.
        self.assertAlmostEqual(logotyp.estimate_luminance(transparent), 1.0, places=2)
        self.assertIsNone(logotyp.estimate_luminance(None))

    def test_label_with_barcode_corner_marks_and_contrast(self) -> None:
        dark_logo = Image.new("RGBA", (200, 80), (10, 10, 10, 255))
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "etiketter.pdf"
            pdf = canvas.Canvas(str(out), pagesize=A4, pageCompression=1)
            label.draw_single_label(
                pdf, 10 * mm, 200 * mm, 57 * mm, 64 * mm, "Redovisning 2025\nA1-01",
                initial_font_size=12,
                barcode_text="A1-01",
                corner_marks=True,
                logo_contrast=True,
                prepared_logo_image=dark_logo,
            )
            label.draw_single_label(
                pdf, 10 * mm, 100 * mm, 57 * mm, 64 * mm, "",
                initial_font_size=12,
                barcode_text="RVar 2025",
                corner_marks=True,
            )
            pdf.save()
            reader = PdfReader(str(out))
            text = reader.pages[0].extract_text() or ""
            self.assertIn("Redovisning", text)
            self.assertIn("A1-01", text)

    def test_old_calls_still_work(self) -> None:
        """Bakåtkompatibilitet: gamla anrop utan nya argument fungerar."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "gamla.pdf"
            pdf = canvas.Canvas(str(out), pagesize=A4)
            label.draw_single_label(
                pdf, 10 * mm, 250 * mm, 41 * mm, 64 * mm, "Gammalt anrop",
                initial_font_size=12,
            )
            pdf.save()
            self.assertEqual(len(PdfReader(str(out)).pages), 1)


class SettingsNyaNycklarTests(unittest.TestCase):
    """Nya settings-nycklar (§4: dokumenterade, bakåtkompatibla)."""

    def test_new_defaults_present(self) -> None:
        data = settings_store.load_settings(
            Path(tempfile.gettempdir()) / "saknas_installningar.json"
        )
        self.assertEqual(data["verifikat_period"], "manad")
        self.assertEqual(data["verifikat_language"], "se")
        self.assertFalse(data["barcode_labels"])
        self.assertFalse(data["corner_marks"])
        self.assertFalse(data["logo_contrast"])

    def test_new_values_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            data = settings_store.load_settings(path)
            data["verifikat_period"] = "kvartal"
            data["verifikat_language"] = "no"
            data["barcode_labels"] = True
            data["corner_marks"] = True
            data["logo_contrast"] = True
            self.assertTrue(settings_store.save_settings(data, path))
            loaded = settings_store.load_settings(path)
            self.assertEqual(loaded["verifikat_period"], "kvartal")
            self.assertEqual(loaded["verifikat_language"], "no")
            self.assertTrue(loaded["barcode_labels"])
            self.assertTrue(loaded["corner_marks"])
            self.assertTrue(loaded["logo_contrast"])
            # Ogiltiga värden saneras till sträng (som alla strängnycklar).
            data["verifikat_period"] = 123
            self.assertTrue(settings_store.save_settings(data, path))
            self.assertEqual(
                settings_store.load_settings(path)["verifikat_period"], "123"
            )


def _tkinter_available() -> bool:
    """True om tkinter kan importeras (sandlåda kan sakna det)."""
    try:
        import tkinter  # noqa: F401
        return True
    except ImportError:
        return False


class FolderImportSmokeTest(unittest.TestCase):
    """folder.py ska kunna importeras utan display (GUI skapas först vid start).

    Testerna hoppar över om tkinter saknas (t.ex. minimal sandbox-Python) —
    på användarens maskin med normal Python körs de alltid.
    """

    @unittest.skipUnless(_tkinter_available(), "tkinter saknas i miljön")
    def test_folder_imports_cleanly(self) -> None:
        module = importlib.import_module("folder")
        self.assertTrue(hasattr(module, "LabelGUI"))
        self.assertTrue(hasattr(module, "ArkivindexModule"))
        self.assertTrue(hasattr(module, "BarcodeModule"))
        # Hjälpfunktioner för checkrutor/streckkoder finns.
        gui_funcs = (
            module.LabelGUI._included_texts,
            module.LabelGUI._barcode_text_for,
            module.LabelGUI.create_arkivindex_pdf,
        )
        self.assertTrue(all(callable(func) for func in gui_funcs))

    @unittest.skipUnless(_tkinter_available(), "tkinter saknas i miljön")
    def test_barcode_text_extraction_logic(self) -> None:
        """_barcode_text_for körs utan Tk-instans via klassens __func__."""
        import folder

        method = folder.LabelGUI._barcode_text_for

        class _FakeGUI:
            _barcode_text_for = method

        fake = _FakeGUI()
        self.assertEqual(fake._barcode_text_for("Redovisning 2025\nA1-01"), "Redovisning 2025")
        self.assertEqual(fake._barcode_text_for("VERIFIKAT\nJAN\n2\n2026"), "JAN 2 2026")
        self.assertIsNone(fake._barcode_text_for("   "))
        self.assertEqual(fake._barcode_text_for("häst"), "hst")  # åäö tas bort
        self.assertEqual(fake._barcode_text_for("X" * 40), "X" * 24)  # max 24


if __name__ == "__main__":
    unittest.main()
