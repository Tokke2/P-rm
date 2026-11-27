# Fil: Script/settings_store.py — Enkel, robust JSON-lagring av appinställningar
#
# Ingen GUI-kod. Programmet ska fungera även om settings.json saknas,
# är trasig eller innehåller gamla/felaktiga värden.

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict

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
    except (OSError, ValueError, TypeError) as exc:
        print(f"[Inställningar] Kunde inte läsa {path.name}: {exc}")
    return result


def save_settings(settings: Dict[str, Any], path: Path = SETTINGS_PATH) -> bool:
    """Sparar atomiskt så ett avbrott inte lämnar halvskriven JSON."""
    temp_path = None
    try:
        data = {key: _coerce(key, settings.get(key)) for key in DEFAULT_SETTINGS}
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
        )
        temp_path = Path(temp_name)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        return True
    except (OSError, TypeError, ValueError) as exc:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
        print(f"[Inställningar] Kunde inte spara {path.name}: {exc}")
        return False


__all__ = ["SETTINGS_PATH", "DEFAULT_SETTINGS", "load_settings", "save_settings"]
