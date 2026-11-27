# Fil: Script/loggar.py — Loggsystem (AGENTS.md §8)
#
# Komplett loggsystem med TVÅ loggar:
#   * applog  — alla normala händelser (INFO/VARNING)
#   * fellog  — ALLA AKTIVA fel; när ett fel åtgärdats tas det bort
#
# Regler som implementeras:
#   * Felloggen innehåller alla aktiva fel (unika per kod)
#   * Åtgärdat fel → bort från felloggen (resolve_error / clear_errors)
#   * Gårdagens loggposter arkiveras (arkiv/<logg>_<datum>.jsonl)
#   * Arkiverade loggar raderas efter 7 dagar
#
# Ingen GUI-kod och inga externa beroenden — kan användas av folder.py,
# alla Script-moduler och automatiska tester. Skriver ENDAST filer (§9:
# inget terminalfönster krävs).

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent / "Loggar"
APP_LOG_NAME = "app_log.jsonl"
FEL_LOG_NAME = "fel_log.jsonl"
ARKIV_DIR_NAME = "arkiv"
RENSA_EFTER_DAGAR = 7          # arkiverade loggar raderas efter 7 dagar


def _now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _date_of(ts: str) -> str:
    """'2026-11-25 09:00:00' → '2026-11-25'."""
    return (ts or "")[:10]


class LogManager:
    """Hanterar applog, fellog och arkivmappen."""

    def __init__(self, base: Path = BASE_DIR):
        self.base = Path(base)
        self.app_path = self.base / APP_LOG_NAME
        self.fel_path = self.base / FEL_LOG_NAME
        self.arkiv_dir = self.base / ARKIV_DIR_NAME
        self.base.mkdir(parents=True, exist_ok=True)
        self.arkiv_dir.mkdir(parents=True, exist_ok=True)

    # ── Lågnivå: läs/skriv JSONL ─────────────────────────
    @staticmethod
    def _read(path: Path) -> List[Dict[str, Any]]:
        entries: List[Dict[str, Any]] = []
        try:
            if path.is_file():
                with path.open("r", encoding="utf-8") as handle:
                    for line in handle:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                        except ValueError:
                            continue  # hoppa över trasiga rader
                        if isinstance(entry, dict):
                            entries.append(entry)
        except OSError as exc:
            print(f"[Loggar] Kunde inte läsa {path.name}: {exc}")
        return entries

    @staticmethod
    def _write(path: Path, entries: List[Dict[str, Any]]) -> None:
        try:
            with path.open("w", encoding="utf-8") as handle:
                for entry in entries:
                    handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError as exc:
            print(f"[Loggar] Kunde inte skriva {path.name}: {exc}")

    # ── Applog ───────────────────────────────────────────
    def log_app(self, meddelande: str, nivå: str = "INFO") -> None:
        """Lägger till en händelse i apploggen."""
        entry = {"ts": _now_stamp(), "nivå": nivå, "meddelande": str(meddelande)}
        entries = self._read(self.app_path)
        entries.append(entry)
        self._write(self.app_path, entries)

    def recent_app(self, limit: int = 100) -> List[Dict[str, Any]]:
        """De senaste apploggraderna (äldst först)."""
        return self._read(self.app_path)[-max(1, limit):]

    # ── Fellog (aktiva fel) ──────────────────────────────
    def log_error(self, kod: str, meddelande: str, nivå: str = "FEL") -> None:
        """Registrerar/uppdaterar ett AKTIVT fel (unikt per kod).

        Loggas samma kod igen uppdateras tid, meddelande och räknaren —
        felloggen innehåller alltid exakt en rad per aktiv felkod.
        """
        entries = self._read(self.fel_path)
        for entry in entries:
            if entry.get("kod") == kod:
                entry.update({
                    "ts": _now_stamp(),
                    "meddelande": str(meddelande),
                    "nivå": nivå,
                    "antal": int(entry.get("antal", 1)) + 1,
                })
                break
        else:
            entries.append({
                "kod": kod,
                "ts": _now_stamp(),
                "meddelande": str(meddelande),
                "nivå": nivå,
                "antal": 1,
            })
        self._write(self.fel_path, entries)

    def resolve_error(self, kod: str) -> bool:
        """Tar bort ett aktivt fel när det åtgärdats. True om det fanns."""
        entries = self._read(self.fel_path)
        remaining = [entry for entry in entries if entry.get("kod") != kod]
        if len(remaining) == len(entries):
            return False
        self._write(self.fel_path, remaining)
        return True

    def clear_errors(self, koder: Optional[List[str]] = None) -> int:
        """Rensar fel manuellt — None/[] = alla, annars bara angivna koder.

        Returnerar antalet borttagna fel.
        """
        entries = self._read(self.fel_path)
        if not koder:
            removed, remaining = len(entries), []
        else:
            wanted = set(koder)
            removed = sum(1 for entry in entries if entry.get("kod") in wanted)
            remaining = [
                entry for entry in entries if entry.get("kod") not in wanted
            ]
        if removed:
            self._write(self.fel_path, remaining)
        return removed

    def active_errors(self) -> List[Dict[str, Any]]:
        """Alla aktiva fel (felloggens innehåll)."""
        return self._read(self.fel_path)

    # ── Arkiv & rensning ─────────────────────────────────
    def archive_yesterday(self) -> Dict[str, int]:
        """Arkiverar gårdagens loggposter.

        * Applog: gamla rader FLYTTAS till arkiv/app_log_<igår>.jsonl.
        * Fellog: gårdagens fel SNAPSHOT:as till arkiv/fel_log_<igår>.jsonl
          (aktiva fel stannar kvar i felloggen tills de åtgärdats).
        """
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        moved = {"app": 0, "fel": 0}

        # Applog: flytta allt som INTE är från idag.
        app_entries = self._read(self.app_path)
        keep = [entry for entry in app_entries
                if _date_of(entry.get("ts", today)) >= today]
        old = [entry for entry in app_entries
               if _date_of(entry.get("ts", today)) < today]
        if old:
            self._merge_archive(self.arkiv_dir / f"app_log_{yesterday}.jsonl", old)
            self._write(self.app_path, keep)
            moved["app"] = len(old)

        # Fellog: snapshot av gårdagens fel (aktiva stannar).
        fel_entries = self._read(self.fel_path)
        yesterday_errors = [
            entry for entry in fel_entries
            if _date_of(entry.get("ts", today)) == yesterday
        ]
        if yesterday_errors:
            self._merge_archive(
                self.arkiv_dir / f"fel_log_{yesterday}.jsonl", yesterday_errors
            )
            moved["fel"] = len(yesterday_errors)
        return moved

    def _merge_archive(self, path: Path, new_entries: List[Dict[str, Any]]) -> None:
        """Lägger till poster i arkivfilen utan dubletter (ts+meddelande)."""
        existing = self._read(path)
        seen = {
            (entry.get("ts"), entry.get("meddelande")) for entry in existing
        }
        for entry in new_entries:
            key = (entry.get("ts"), entry.get("meddelande"))
            if key not in seen:
                existing.append(entry)
                seen.add(key)
        self._write(path, existing)

    def cleanup_archive(self, days: int = RENSA_EFTER_DAGAR) -> List[str]:
        """Raderar arkiverade loggar äldre än *days* dagar (standard 7)."""
        if days < 1:
            raise ValueError("days måste vara >= 1.")
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        deleted: List[str] = []
        for path in self.arkiv_dir.glob("*.jsonl"):
            date_part = path.stem.rsplit("_", 1)[-1]  # …_2026-11-18
            if len(date_part) == 10 and date_part < cutoff:
                try:
                    path.unlink()
                    deleted.append(path.name)
                except OSError as exc:
                    print(f"[Loggar] Kunde inte radera {path.name}: {exc}")
        return deleted

    def daily_housekeeping(self) -> Dict[str, Any]:
        """Körs vid appstart: arkivera gårdagens loggar + rensa arkivet."""
        moved = self.archive_yesterday()
        deleted = self.cleanup_archive()
        return {"arkiverade": moved, "raderade": deleted}


# Delad standardinstans för hela appen.
logg = LogManager()


__all__ = [
    "BASE_DIR",
    "APP_LOG_NAME",
    "FEL_LOG_NAME",
    "ARKIV_DIR_NAME",
    "RENSA_EFTER_DAGAR",
    "LogManager",
    "logg",
]
