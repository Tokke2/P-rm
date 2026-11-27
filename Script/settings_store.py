# Fil: Script/settings_store.py — Enkel, robust JSON-lagring av appinställningar
#
# Ingen GUI-kod. Programmet ska fungera även om settings.json saknas,
# är trasig eller innehåller gamla/felaktiga värden.

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict

try:
    from Script import loggar as _LoggModule
except ImportError:  # kör filen direkt ur Script-mappen
    import loggar as _LoggModule  # type: ignore[no-redef]

SETTINGS_PATH = Path(__file__).resolve().parent.parent / "settings.json"

DEFAULT_SETTINGS: Dict[str, Any] = {
    "label_type": "rygg_smal",
    "text_size": 16,
    "auto_shrink": True,
    "multi_label": False,
    "cut_lines": True,
    "logo_top_px": 5,
    "label_count": 1,
    "verifikat_year": 0,          # 0 = aktuellt år
    "verifikat_per_month": 2,
    "verifikat_period": "manad",  # manad | kvartal | halvar  (förslag #10)
    "verifikat_language": "se",   # se | en | no             (förslag #11)
    "barcode_labels": False,      # Code 128-B på etiketter   (förslag #2)
    "corner_marks": False,        # förstärkta hörnmarkeringar (förslag #22)
    "logo_contrast": False,       # automatisk logotypkontrast (förslag #16)
    "auto_update_daily": True,    # auto-uppdatering 00:00 varje dag (REQ-K4)
    "minimize_to_tray": False,    # stäng = minimera till systemfältet (#1)
    "separate_row_pdfs": False,   # även en PDF per rad utöver samlad (#5)
    "gui_language": "sv",         # gränssnittsspråk: sv | en (#7)
    "last_logo_path": "",
    "window_geometry": "",
}

# Intern backup (§9-diagnos): uppdateras vid VARJE lyckad sparning och
# används för att reparera en korrupt settings.json (förslag #9).
SETTINGS_BAK_PATH = SETTINGS_PATH.with_suffix(".json.bak")


def diagnose_settings(
    path: Path = SETTINGS_PATH,
    bak_path: Path = SETTINGS_BAK_PATH,
) -> bool:
    """Självdiagnos av settings.json (förslag #9).

    • Filen OK → uppdatera intern backup (.bak) och returnera False
      (inget reparerat).
    • Filen korrupt/skrivskyddstrasslig → återställ från intern backup
      (eller skapa färsk standardfil) och returnera True.
    Kraschar ALDRIG — alla fel loggas och hanteras.
    """
    try:
        if not path.exists():
            save_settings(dict(DEFAULT_SETTINGS), path)
            try:
                save_settings(dict(DEFAULT_SETTINGS), bak_path)
            except Exception:
                pass
            return False
        # Testläs — load_settings fångar själva felet och loggar.
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("rot-element är inte ett objekt")
        save_settings(data, bak_path)  # frisk backup av giltig fil
        return False
    except Exception:
        # Korrupt fil → reparera från .bak (eller färsk standard).
        try:
            if bak_path.is_file():
                json.loads(bak_path.read_text(encoding="utf-8"))
                shutil.copyfile(bak_path, path)
                source = "intern backup"
            else:
                save_settings(dict(DEFAULT_SETTINGS), path)
                source = "standardinställningar"
            _LoggModule.logg.log_app(
                f"SETTINGS-DIAGNOS: korrupt settings.json reparerad "
                f"från {source}"
            )
            return True
        except Exception as exc:
            _LoggModule.logg.log_error(
                "SETTINGS_READ", f"Diagnos/reparation misslyckades: {exc}"
            )
            return False


def _coerce(key: str, value: Any) -> Any:
    """Sanera ett sparat värde till rätt typ (med DEFAULT som fallback)."""
    default = DEFAULT_SETTINGS[key]
    if isinstance(default, bool):
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)
    if isinstance(default, int):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
    if isinstance(default, str):
        return str(value) if value is not None else default
    return value


def load_settings(path: Path = SETTINGS_PATH) -> Dict[str, Any]:
    """Läser settings.json. Returnerar alltid en komplett dict."""
    result = dict(DEFAULT_SETTINGS)
    try:
        if path.is_file():
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                for key in result:
                    if key in data:
                        result[key] = _coerce(key, data[key])
        _LoggModule.logg.resolve_error("SETTINGS_READ")
    except (OSError, ValueError, TypeError) as exc:
        print(f"[Inställningar] Kunde inte läsa {path.name}: {exc}")
        _LoggModule.logg.log_error("SETTINGS_READ", f"Kunde inte läsa {path.name}: {exc}")
    return result


def save_settings(settings: Dict[str, Any], path: Path = SETTINGS_PATH) -> bool:
    """Sparar inställningar atomiskt + uppdaterar intern backup (.bak)."""
    try:
        data = {key: _coerce(key, settings.get(key)) for key in DEFAULT_SETTINGS}
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False, sort_keys=True)
        tmp.replace(path)  # atomisk byt — ingen halvskriven fil kan läsas
        try:
            shutil.copyfile(path, path.with_suffix(".json.bak"))
        except OSError:
            pass  # backup är ett skyddsnät, aldrig en stoppblock
        _LoggModule.logg.resolve_error("SETTINGS_SAVE")
        return True
    except (OSError, TypeError, ValueError) as exc:
        print(f"[Inställningar] Kunde inte spara {path.name}: {exc}")
        _LoggModule.logg.log_error("SETTINGS_SAVE", f"Kunde inte spara {path.name}: {exc}")
        return False


__all__ = [
    "SETTINGS_PATH", "SETTINGS_BAK_PATH", "DEFAULT_SETTINGS",
    "load_settings", "save_settings", "diagnose_settings",
]
