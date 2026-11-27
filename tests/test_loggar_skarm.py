"""Tester för v1.2.0: loggsystem (§8), skärm/DPI (§11), SVG-aspektfix.

Kör: python -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image  # noqa: E402

from Script import loggar, logotyp, skarm  # noqa: E402


class LoggSystemTests(unittest.TestCase):
    """§8: applog + fellog (aktiva fel), arkiv, 7-dagars rensning."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.logg = loggar.LogManager(Path(self.tmp.name) / "Loggar")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    # ── Applog ───────────────────────────────────────────
    def test_applog_append_and_recent(self) -> None:
        self.logg.log_app("Första händelsen")
        self.logg.log_app("Andra händelsen", "VARNING")
        recent = self.logg.recent_app(10)
        self.assertEqual(len(recent), 2)
        self.assertEqual(recent[0]["meddelande"], "Första händelsen")
        self.assertEqual(recent[1]["nivå"], "VARNING")
        self.assertIn("ts", recent[0])

    # ── Fellog: aktiva fel ───────────────────────────────
    def test_error_is_active_and_unique_per_code(self) -> None:
        self.logg.log_error("LOGO_LOAD", "Kunde inte läsa logo.pdf")
        self.logg.log_error("LOGO_LOAD", "Kunde inte läsa logo2.pdf")
        active = self.logg.active_errors()
        self.assertEqual(len(active), 1)  # unik per kod
        self.assertEqual(active[0]["meddelande"], "Kunde inte läsa logo2.pdf")
        self.assertEqual(active[0]["antal"], 2)

    def test_resolved_error_removed_automatically(self) -> None:
        self.logg.log_error("PDF_CREATE", "fel vid skapande")
        self.assertTrue(self.logg.resolve_error("PDF_CREATE"))
        self.assertEqual(self.logg.active_errors(), [])
        self.assertFalse(self.logg.resolve_error("PDF_CREATE"))  # fanns inte

    def test_manual_clearing_selected_and_all(self) -> None:
        self.logg.log_error("A", "fel a")
        self.logg.log_error("B", "fel b")
        self.logg.log_error("C", "fel c")
        self.assertEqual(self.logg.clear_errors(["A", "C"]), 2)
        remaining = [entry["kod"] for entry in self.logg.active_errors()]
        self.assertEqual(remaining, ["B"])
        self.assertEqual(self.logg.clear_errors(None), 1)
        self.assertEqual(self.logg.active_errors(), [])

    # ── Arkivering: gårdagens poster ─────────────────────
    def test_yesterday_app_lines_are_archived(self) -> None:
        yesterday = datetime.now() - timedelta(days=1)
        with self.logg.app_path.open("w", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "ts": yesterday.strftime("%Y-%m-%d 10:00:00"),
                "nivå": "INFO", "meddelande": "gammal händelse",
            }) + "\n")
            handle.write(json.dumps({
                "ts": datetime.now().strftime("%Y-%m-%d 12:00:00"),
                "nivå": "INFO", "meddelande": "dagens händelse",
            }) + "\n")

        moved = self.logg.archive_yesterday()
        self.assertEqual(moved["app"], 1)
        # Gammal rad → arkiv, dagens → kvar.
        archive = self.logg.arkiv_dir / (
            f"app_log_{yesterday.strftime('%Y-%m-%d')}.jsonl"
        )
        self.assertTrue(archive.is_file())
        self.assertEqual(len(self.logg.recent_app(10)), 1)
        self.assertEqual(
            self.logg.recent_app(10)[0]["meddelande"], "dagens händelse"
        )

    def test_yesterday_errors_snapshotted_but_active_kept(self) -> None:
        yesterday = datetime.now() - timedelta(days=1)
        self.logg.log_error("GAMMALT", "fel från igår")
        # Skriv om ts till igår (log_error använder nu).
        entries = self.logg.active_errors()
        entries[0]["ts"] = yesterday.strftime("%Y-%m-%d 09:00:00")
        self.logg._write(self.logg.fel_path, entries)

        moved = self.logg.archive_yesterday()
        self.assertEqual(moved["fel"], 1)
        # Snapshot i arkivet …
        archive = self.logg.arkiv_dir / (
            f"fel_log_{yesterday.strftime('%Y-%m-%d')}.jsonl"
        )
        self.assertTrue(archive.is_file())
        # … men felet är fortfarande AKTIVT i felloggen.
        self.assertEqual(len(self.logg.active_errors()), 1)

    # ── Rensning: arkiv raderas efter 7 dagar ────────────
    def test_cleanup_archive_after_7_days(self) -> None:
        old_date = datetime.now() - timedelta(days=8)
        fresh_date = datetime.now() - timedelta(days=3)
        old_file = self.logg.arkiv_dir / (
            f"app_log_{old_date.strftime('%Y-%m-%d')}.jsonl"
        )
        fresh_file = self.logg.arkiv_dir / (
            f"app_log_{fresh_date.strftime('%Y-%m-%d')}.jsonl"
        )
        old_file.write_text("{}\n", encoding="utf-8")
        fresh_file.write_text("{}\n", encoding="utf-8")

        deleted = self.logg.cleanup_archive()
        self.assertEqual(deleted, [old_file.name])
        self.assertFalse(old_file.exists())
        self.assertTrue(fresh_file.exists())
        with self.assertRaises(ValueError):
            self.logg.cleanup_archive(0)

    def test_housekeeping_runs_both(self) -> None:
        summary = self.logg.daily_housekeeping()
        self.assertIn("arkiverade", summary)
        self.assertIn("raderade", summary)

    def test_corrupt_lines_skipped(self) -> None:
        with self.logg.app_path.open("w", encoding="utf-8") as handle:
            handle.write("{inte json}\n")
            handle.write(json.dumps({
                "ts": datetime.now().strftime("%Y-%m-%d 09:00:00"),
                "nivå": "INFO", "meddelande": "giltig",
            }) + "\n")
        recent = self.logg.recent_app(10)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0]["meddelande"], "giltig")


class SkarmTests(unittest.TestCase):
    """§11: startgeometri (max höjd, anpassad bredd) + DPI-hjälp."""

    def test_geometry_max_height_full_hd(self) -> None:
        geo = skarm.compute_start_geometry(1920, 1080)
        main, x, y = geo.replace("+", " ").split()
        width, height = main.split("x")
        # Höjd = 1080 − taskbar − marginal = 1080 − 72 − 16 = 992.
        self.assertEqual(int(height), 1080 - skarm.TASKBAR_RESERVE - skarm.EDGE_MARGIN)
        # Bredd = 62 % av skärmen när inget sparat värde finns.
        self.assertEqual(int(width), int(1920 * 0.62))
        self.assertEqual(int(x), (1920 - int(width)) // 2)  # centrerad
        self.assertEqual(int(y), 8)  # liten toppmarginal

    def test_geometry_uses_saved_width(self) -> None:
        geo = skarm.compute_start_geometry(1920, 1080, "1100x700+40+20")
        main, _x, _y = geo.replace("+", " ").split()
        self.assertEqual(int(main.split("x")[0]), 1100)  # breddminne bevaras

    def test_geometry_clamps_to_screen(self) -> None:
        geo = skarm.compute_start_geometry(1024, 768, "1800x600+0+0")
        main, _x, _y = geo.replace("+", " ").split()
        width = int(main.split("x")[0])
        self.assertLessEqual(width, 1024 - 2 * skarm.EDGE_MARGIN)
        self.assertGreaterEqual(width, skarm.MIN_WIDTH)

    def test_geometry_small_screen(self) -> None:
        geo = skarm.compute_start_geometry(800, 600)
        main, _x, _y = geo.replace("+", " ").split()
        width, height = main.split("x")
        self.assertEqual(int(height), 600)  # 600−72−16 → minst 600
        self.assertLess(int(width), 800)    # ryms på skärmen

    def test_geometry_invalid_screen(self) -> None:
        self.assertEqual(
            skarm.compute_start_geometry(0, 0), "1024x720+80+40"
        )

    def test_parse_geometry(self) -> None:
        self.assertEqual(skarm.parse_geometry("1100x700+40+20"), 1100)
        self.assertIsNone(skarm.parse_geometry("ogiltigt"))
        self.assertIsNone(skarm.parse_geometry(""))

    def test_dpi_awareness_noop_without_windows(self) -> None:
        # På Linux/sandbox → False; på Windows → True (kan inte testas här).
        if sys.platform.startswith("win"):
            self.assertTrue(skarm.enable_dpi_awareness())
        else:
            self.assertFalse(skarm.enable_dpi_awareness())


class AppLogotypTests(unittest.TestCase):
    """Appens logotyp: vektor-SVG fungerar som logotyp + ikonerna finns."""

    def test_svg_and_icons_exist_and_are_readable(self) -> None:
        assets = Path(__file__).resolve().parent.parent / "assets"
        svg = assets / "app_logotyp.svg"
        icon512 = assets / "app_logotyp_512.png"
        icon128 = assets / "app_logotyp_128.png"
        self.assertTrue(svg.is_file())
        self.assertTrue(icon512.is_file())
        self.assertTrue(icon128.is_file())
        svg_text = svg.read_text(encoding="utf-8")
        self.assertIn("<svg", svg_text)  # redigerbar vektor för tryck
        for name in (icon512, icon128):
            with Image.open(name) as img:
                self.assertEqual(img.size, (512, 512) if "512" in name.name
                                 else (128, 128))
                self.assertEqual(img.mode, "RGBA")

    def test_app_logotype_loads_through_pipeline(self) -> None:
        assets = Path(__file__).resolve().parent.parent / "assets"
        image = logotyp.load_and_resize_logo(
            str(assets / "app_logotyp.svg"), max_width_mm=40
        )
        self.assertIsNotNone(image)
        # Beskuren pärmrygg: högre än bred (336×432-proportioner).
        self.assertGreater(image.height, image.width)

    def test_svg_aspect_ratio_preserved(self) -> None:
        """Regression: kvadratisk SVG → kvadratisk render (stream-bugg fixad)."""
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "kvadrat.svg"
            source.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="200" '
                'height="200"><rect width="200" height="200" '
                'fill="#2244cc"/></svg>', encoding="utf-8",
            )
            image = logotyp.load_and_resize_logo(str(source), max_width_mm=40)
            self.assertIsNotNone(image)
            ratio = image.height / image.width
            self.assertAlmostEqual(ratio, 1.0, delta=0.05)


if __name__ == "__main__":
    unittest.main()
