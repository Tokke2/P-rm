# Fil: Script/settings_store.py — Enkel, robust JSON-lagring av appinställningar
#
# Ingen GUI-kod. Programmet ska fungera även om settings.json saknas,
# är trasig eller innehåller gamla/felaktiga värden.

from __future__ import annotations

import json
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
    "last_logo_path": "",
    "window_geometry": "",
}


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
    """Sparar inställningar. Returnerar True vid lyckad skrivning."""
    try:
        data = {key: _coerce(key, settings.get(key)) for key in DEFAULT_SETTINGS}
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False, sort_keys=True)
        _LoggModule.logg.resolve_error("SETTINGS_SAVE")
        return True
    except (OSError, TypeError, ValueError) as exc:
        print(f"[Inställningar] Kunde inte spara {path.name}: {exc}")
        _LoggModule.logg.log_error("SETTINGS_SAVE", f"Kunde inte spara {path.name}: {exc}")
        return False


__all__ = ["SETTINGS_PATH", "DEFAULT_SETTINGS", "load_settings", "save_settings"]
