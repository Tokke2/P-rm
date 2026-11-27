"""Tester för filjämförande uppdaterare (REQ-K4, §3) — helt offline.

Nätverksdelarna injiceras (fetch_info/download_archive) så att testerna
aldrig använder nätet. Kör: python -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Script import loggar, updater  # noqa: E402


def _write(root: Path, rel: str, content: str) -> Path:
    path = Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


class VersionTests(unittest.TestCase):
    def test_parse_version(self) -> None:
        self.assertEqual(updater.parse_version("1.2.0"), (1, 2, 0))
        self.assertEqual(updater.parse_version("v1.2.0"), (1, 2, 0))
        self.assertEqual(updater.parse_version("v2"), (2, 0, 0))
        self.assertEqual(updater.parse_version("ogiltigt"), (0, 0, 0))

    def test_is_newer_release(self) -> None:
        self.assertTrue(updater.is_newer_release("v1.3.0", "1.2.0"))
        self.assertFalse(updater.is_newer_release("v1.2.0", "1.2.0"))
        self.assertFalse(updater.is_newer_release("1.1.9", "1.2.0"))

    def test_read_installed_version_missing_file(self) -> None:
        self.assertEqual(updater.read_installed_version(
            Path(tempfile.gettempdir()) / "finns_ej_VERSION.txt"
        ), "0.0.0")


class CompareTests(unittest.TestCase):
    """REQ-K4: jämför filnamn + innehåll — endast skillnaden."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.current = Path(self.tmp.name) / "nu"
        self.release = Path(self.tmp.name) / "release"
        self.current.mkdir()
        self.release.mkdir()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_compare_detects_add_update_remove(self) -> None:
        _write(self.current, "folder.py", "GAMMALT")
        _write(self.current, "gammal_modul.py", "raderas")
        _write(self.release, "folder.py", "NYTT")
        _write(self.release, "ny_modul.py", "ny fil")

        diff = updater.compare_files(self.current, self.release)
        self.assertEqual(diff["to_update"], ["folder.py"])
        self.assertEqual(diff["to_add"], ["ny_modul.py"])
        self.assertEqual(diff["to_remove"], ["gammal_modul.py"])
        self.assertEqual(diff["unchanged"], [])

    def test_compare_identical_roots(self) -> None:
        _write(self.current, "a.txt", "samma")
        _write(self.release, "a.txt", "samma")
        diff = updater.compare_files(self.current, self.release)
        self.assertEqual(diff["to_update"], [])
        self.assertEqual(diff["to_add"], [])
        self.assertEqual(diff["to_remove"], [])
        self.assertEqual(diff["unchanged"], ["a.txt"])

    def test_user_data_is_never_managed(self) -> None:
        # settings.json + Loggar/ + Logotyp/ + export/ + backup katalogen
        # ingår ALDRIG i jämförelsen (användardata skyddas).
        _write(self.current, "settings.json", "{}")
        _write(self.current, "Loggar/app_log.jsonl", "logg")
        _write(self.current, "export/test.pdf", "pdf")
        _write(self.release, "settings.json", "{\"nyckel\": 1}")
        _write(self.release, "Loggar/app_log.jsonl", "annan logg")
        diff = updater.compare_files(self.current, self.release)
        managed = set(
            diff["to_update"] + diff["to_add"]
            + diff["to_remove"] + diff["unchanged"]
        )
        self.assertNotIn("settings.json", managed)
        self.assertNotIn("Loggar/app_log.jsonl", managed)
        self.assertNotIn("export/test.pdf", managed)
        self.assertEqual(managed, set())


class ApplyUpdateTests(unittest.TestCase):
    """Backup → applicera → verifiera → backup tas bort ENDAST vid lyckat."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.current = Path(self.tmp.name) / "nu"
        self.release = Path(self.tmp.name) / "release"
        self.current.mkdir()
        self.release.mkdir()
        # Återställ backupmappen mellan tester.
        if updater.BACKUP_DIR.exists():
            import shutil
            shutil.rmtree(updater.BACKUP_DIR)

    def tearDown(self) -> None:
        self.tmp.cleanup()
        import shutil
        if updater.BACKUP_DIR.exists():
            shutil.rmtree(updater.BACKUP_DIR)

    def _setup_mixed_diff(self) -> Dict[str, List[str]]:
        _write(self.current, "folder.py", "GAMMALT")
        _write(self.current, "gammal_modul.py", "raderas")
        _write(self.current, "oforandrad.py", "samma")
        _write(self.release, "folder.py", "NYTT")
        _write(self.release, "ny_modul.py", "ny fil")
        _write(self.release, "oforandrad.py", "samma")
        return updater.compare_files(self.current, self.release)

    def test_apply_success_and_backup_removed(self) -> None:
        diff = self._setup_mixed_diff()
        result = updater.apply_update(self.current, self.release, diff)
        self.assertTrue(result["ok"])
        self.assertTrue(result["verified"])
        self.assertTrue(result["backup_removed"])
        # Filerna ska nu matcha releasen exakt.
        self.assertEqual(
            updater.build_file_hashes(self.current),
            updater.build_file_hashes(self.release),
        )
        self.assertEqual(
            (self.current / "folder.py").read_text(encoding="utf-8"), "NYTT"
        )
        self.assertFalse((self.current / "gammal_modul.py").exists())
        self.assertTrue((self.current / "ny_modul.py").exists())
        # Backupmappen är BORTTAGEN efter lyckad verifiering (§3).
        self.assertFalse(updater.BACKUP_DIR.exists())

    def test_verify_failure_rolls_back_everything(self) -> None:
        diff = self._setup_mixed_diff()
        original_folder = (self.current / "folder.py").read_text(encoding="utf-8")

        # Tvinga verifieringsfel via monkeypatch av _verifieringskällan.
        original_hashes = updater.build_file_hashes

        def falsk_hash(root):
            hashes = original_hashes(root)
            if root == self.current:
                hashes["folder.py"] = "0" * 64  # fejkad mismatch
            return hashes

        updater.build_file_hashes = falsk_hash
        try:
            result = updater.apply_update(self.current, self.release, diff)
        finally:
            updater.build_file_hashes = original_hashes

        self.assertFalse(result["ok"])
        # Rollback: allt är som före uppdateringen.
        self.assertEqual(
            (self.current / "folder.py").read_text(encoding="utf-8"),
            original_folder,
        )
        self.assertEqual(
            (self.current / "gammal_modul.py").read_text(encoding="utf-8"),
            "raderas",
        )
        self.assertFalse((self.current / "ny_modul.py").exists())
        self.assertFalse(updater.BACKUP_DIR.exists())

    def test_backup_dir_used_during_apply(self) -> None:
        """Backup skapas under appliceringen (kontrolleras via _backup_files)."""
        _write(self.current, "folder.py", "GAMMALT")
        count = updater._backup_files(self.current, ["folder.py"])
        self.assertEqual(count, 1)
        backup_file = updater.BACKUP_DIR / "folder.py"
        self.assertEqual(
            backup_file.read_text(encoding="utf-8"), "GAMMALT"
        )


class RunUpdateTests(unittest.TestCase):
    """Hela flödet med injicerade (offline) nätverksfunktioner."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.app = Path(self.tmp.name) / "app"
        self.app.mkdir()
        _write(self.app, "VERSION.txt", "1.2.0\n")
        _write(self.app, "folder.py", "GAMMALT INNEHÅLL")
        _write(self.app, "settings.json", "{}")
        self.logg = loggar.LogManager(Path(self.tmp.name) / "Loggar")
        if updater.BACKUP_DIR.exists():
            import shutil
            shutil.rmtree(updater.BACKUP_DIR)

    def tearDown(self) -> None:
        self.tmp.cleanup()
        import shutil
        if updater.BACKUP_DIR.exists():
            shutil.rmtree(updater.BACKUP_DIR)

    def _fake_archive(self, tag: str, dest_dir: Path) -> Path:
        """Bygger en riktig tar.gz som representerar releasen."""
        staging = Path(self.tmp.name) / "staging" / f"P-rm-{tag.lstrip('v')}"
        _write(staging, "VERSION.txt", tag.lstrip("v") + "\n")
        _write(staging, "folder.py", "NYTT INNEHÅLL")
        _write(staging, "ny_modul.py", "ny fil")
        dest_dir.mkdir(parents=True, exist_ok=True)
        archive = dest_dir / "release.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(staging, arcname=staging.name)
        return archive

    def test_full_update_flow(self) -> None:
        info = {"tag": "v1.3.0", "name": "Test", "target_commitish":
                "arena/684c29e9-p-rm"}
        result = updater.run_update(
            self.app,
            fetch_info=lambda: info,
            download_archive=self._fake_archive,
            log=self.logg,
        )
        self.assertTrue(result["ok"], result)
        self.assertTrue(result["uppdaterad"])
        # Filerna uppdaterade:
        self.assertEqual(
            (self.app / "VERSION.txt").read_text(encoding="utf-8").strip(),
            "1.3.0",
        )
        self.assertEqual(
            (self.app / "folder.py").read_text(encoding="utf-8"),
            "NYTT INNEHÅLL",
        )
        self.assertTrue((self.app / "ny_modul.py").exists())
        # Användardata orörd:
        self.assertEqual(
            (self.app / "settings.json").read_text(encoding="utf-8"), "{}"
        )
        # Backup borttagen efter lyckad verifiering:
        self.assertFalse(updater.BACKUP_DIR.exists())
        # Loggning: händelser i applog, inga aktiva UPD-fel.
        messages = [entry["meddelande"] for entry in self.logg.recent_app(50)]
        self.assertTrue(any("Uppdatering startad" in m for m in messages))
        self.assertTrue(any("Uppdatering till v1.3.0 klar" in m for m in messages))
        self.assertEqual(
            [e for e in self.logg.active_errors()
             if e["kod"].startswith("UPD")], []
        )

    def test_already_latest(self) -> None:
        info = {"tag": "v1.2.0", "name": "Test", "target_commitish":
                "arena/684c29e9-p-rm"}
        result = updater.run_update(
            self.app,
            fetch_info=lambda: info,
            download_archive=self._fake_archive,
            log=self.logg,
        )
        self.assertTrue(result["ok"])
        self.assertFalse(result["uppdaterad"])
        self.assertIn("Redan senaste", result["meddelande"])
        self.assertEqual(
            (self.app / "folder.py").read_text(encoding="utf-8"),
            "GAMMALT INNEHÅLL",
        )

    def test_refuses_main_target(self) -> None:
        """§1: releaser som pekar på main vägras (HÅRD)."""
        info = {"tag": "v9.9.9", "name": "Test", "target_commitish": "main"}
        result = updater.run_update(
            self.app,
            fetch_info=lambda: info,
            download_archive=self._fake_archive,
            log=self.logg,
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["steg"], "check")
        self.assertIn("main", result["fel"])
        active_codes = [e["kod"] for e in self.logg.active_errors()]
        self.assertIn("UPD_CHECK", active_codes)
        # Ingen fil ändrad:
        self.assertEqual(
            (self.app / "VERSION.txt").read_text(encoding="utf-8").strip(),
            "1.2.0",
        )

    def test_network_failure_is_logged(self) -> None:
        def fel_info():
            raise OSError("nätet borta")

        result = updater.run_update(
            self.app, fetch_info=fel_info, log=self.logg,
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["steg"], "check")
        active_codes = [e["kod"] for e in self.logg.active_errors()]
        self.assertIn("UPD_CHECK", active_codes)
        # Efter lyckad check senare skulle felet försvinna —
        # resolve_error-anropet testas i test_full_update_flow.

    def test_check_for_new_release(self) -> None:
        info = {"tag": "v1.3.0", "name": "Test", "target_commitish":
                "arena/684c29e9-p-rm"}
        result = updater.check_for_new_release(
            fetch_info=lambda: info, version_path=self.app / "VERSION.txt"
        )
        self.assertTrue(result["ny_release"])
        self.assertEqual(result["tag"], "v1.3.0")
        self.assertEqual(result["installed"], "1.2.0")

    def test_check_for_new_release_refuses_main(self) -> None:
        info = {"tag": "v9.9.9", "name": "Test", "target_commitish": "main"}
        with self.assertRaises(updater.UpdaterError):
            updater.check_for_new_release(
                fetch_info=lambda: info, version_path=self.app / "VERSION.txt"
            )

    def test_extract_archive_returns_inner_root(self) -> None:
        staging = Path(self.tmp.name) / "staging" / "P-rm-1.3.0"
        _write(staging, "hej.txt", "innehåll")
        archive = Path(self.tmp.name) / "release.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(staging, arcname=staging.name)
        extracted = updater.extract_archive(archive, Path(self.tmp.name) / "ut")
        self.assertEqual(extracted.name, "P-rm-1.3.0")
        self.assertTrue((extracted / "hej.txt").is_file())

    def test_real_repo_hashes_exclude_user_data(self) -> None:
        """Sanity på riktiga repot: settings.json/Loggar hanteras aldrig."""
        hashes = updater.build_file_hashes(Path(__file__).resolve().parent.parent)
        self.assertIn("folder.py", hashes)
        self.assertNotIn("settings.json", hashes)
        self.assertTrue(
            all(not rel.startswith("Loggar/") for rel in hashes)
        )


class AutoUpdTests(unittest.TestCase):
    """Auto-uppdatering 00:00 varje dag (schemaläggning + tyst flöde)."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.app = Path(self.tmp.name) / "app"
        self.app.mkdir()
        _write(self.app, "VERSION.txt", "1.2.0\n")
        self.logg = loggar.LogManager(Path(self.tmp.name) / "Loggar")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _fake_archive(self, tag: str, dest_dir: Path) -> Path:
        staging = Path(self.tmp.name) / "staging" / f"P-rm-{tag.lstrip('v')}"
        _write(staging, "VERSION.txt", tag.lstrip("v") + "\n")
        _write(staging, "folder.py", "AUTO-UPPDATERAD")
        dest_dir.mkdir(parents=True, exist_ok=True)
        archive = dest_dir / "release.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(staging, arcname=staging.name)
        return archive

    # ── next_midnight_delay (pure, tidsinjektion) ────────
    def test_delay_daytime_is_until_next_midnight(self) -> None:
        from datetime import datetime

        noon = datetime(2026, 11, 25, 12, 0, 0)
        self.assertEqual(updater.next_midnight_delay(noon), 12 * 3600 * 1000)
        late = datetime(2026, 11, 25, 23, 59, 0)
        self.assertEqual(updater.next_midnight_delay(late), 60 * 1000)
        evening = datetime(2026, 11, 25, 22, 0, 0)
        self.assertEqual(updater.next_midnight_delay(evening), 2 * 3600 * 1000)

    def test_delay_catchup_right_after_midnight(self) -> None:
        from datetime import datetime

        self.assertEqual(updater.next_midnight_delay(
            datetime(2026, 11, 25, 0, 0, 0)), 0)
        self.assertEqual(updater.next_midnight_delay(
            datetime(2026, 11, 25, 0, 3, 0)), 0)  # inom 5-min-fönstret

    def test_delay_just_after_catchup_window(self) -> None:
        from datetime import datetime

        delay = updater.next_midnight_delay(datetime(2026, 11, 25, 0, 6, 0))
        expected = int(23 * 3600 * 1000 + 54 * 60 * 1000)
        self.assertAlmostEqual(delay, expected, delta=1500)

    def test_delay_with_custom_catchup_window(self) -> None:
        from datetime import datetime

        self.assertEqual(updater.next_midnight_delay(
            datetime(2026, 11, 25, 0, 10, 0), catchup_minutes=15), 0)

    # ── auto_update: tyst flöde, alltid loggning ─────────
    def test_auto_update_applies_new_release_silently(self) -> None:
        info = {"tag": "v1.3.0", "name": "T", "target_commitish":
                "arena/684c29e9-p-rm"}
        result = updater.auto_update(
            self.app,
            log=self.logg,
            fetch_info=lambda: info,
            download_archive=self._fake_archive,
        )
        self.assertTrue(result["ok"] and result["uppdaterad"])
        self.assertEqual(
            (self.app / "VERSION.txt").read_text(encoding="utf-8").strip(),
            "1.3.0",
        )
        messages = [entry["meddelande"] for entry in self.logg.recent_app(50)]
        self.assertTrue(any("AUTO-UPD: schemalagd" in m for m in messages))
        self.assertTrue(any("AUTO-UPD: uppdaterade till v1.3.0" in m for m in messages))
        # Inga aktiva UPD-fel efter lyckad auto-uppdatering:
        self.assertEqual(
            [e for e in self.logg.active_errors()
             if e["kod"].startswith("UPD")], []
        )

    def test_auto_update_no_update_needed(self) -> None:
        info = {"tag": "v1.2.0", "name": "T", "target_commitish":
                "arena/684c29e9-p-rm"}
        result = updater.auto_update(
            self.app,
            log=self.logg,
            fetch_info=lambda: info,
            download_archive=self._fake_archive,
        )
        self.assertTrue(result["ok"] and not result["uppdaterad"])
        messages = [entry["meddelande"] for entry in self.logg.recent_app(50)]
        self.assertTrue(any("AUTO-UPD: ingen uppdatering behövs" in m for m in messages))

    def test_auto_update_failure_goes_to_error_log(self) -> None:
        def fel_info():
            raise OSError("nätet borta")

        result = updater.auto_update(
            self.app, log=self.logg, fetch_info=fel_info,
        )
        self.assertFalse(result["ok"])
        active_codes = [e["kod"] for e in self.logg.active_errors()]
        self.assertIn("UPD_CHECK", active_codes)

    def test_auto_update_refuses_main(self) -> None:
        info = {"tag": "v9.9.9", "name": "T", "target_commitish": "main"}
        result = updater.auto_update(
            self.app, log=self.logg, fetch_info=lambda: info,
        )
        self.assertFalse(result["ok"])
        self.assertIn("main", result["fel"])
        # Inget ändrat:
        self.assertEqual(
            (self.app / "VERSION.txt").read_text(encoding="utf-8").strip(),
            "1.2.0",
        )

    def test_settings_auto_update_roundtrip(self) -> None:
        from Script import settings_store

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            data = settings_store.load_settings(path)
            self.assertTrue(data["auto_update_daily"])  # default på
            data["auto_update_daily"] = False
            settings_store.save_settings(data, path)
            self.assertFalse(
                settings_store.load_settings(path)["auto_update_daily"]
            )


if __name__ == "__main__":
    unittest.main()
