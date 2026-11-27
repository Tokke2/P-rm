# Fil: Script/autostart.py — Autostart vid inloggning (AGENTS.md §9/§11)
#
# Windows: skapar/tar bort ett värde i HKCU\…\CurrentVersion\Run som
# startar appen vid inloggning — med **pythonw.exe** (INGET terminal-
# fönster, §9). Andra plattformar: no-op (False) utan crash.
#
# Injektion: `winreg_module` kan skickas in i testerna (fake-registrering)
# så att logiken testas utan riktig registery och utan Windows.

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_VALUE_NAME = "ParmetikettGenerator"


def _winreg_module() -> Optional[Any]:
    """Returnerar winreg-modulen på Windows, annars None."""
    if not sys.platform.startswith("win"):
        return None
    try:
        import winreg  # noqa: F401
        return winreg
    except ImportError:
        return None


def resolve_pythonw(python_exe: Optional[str] = None) -> str:
    """pythonw.exe bredvid tolken om den finns (ingen konsol, §9)."""
    exe = Path(python_exe or sys.executable)
    pythonw = exe.with_name("pythonw.exe")
    return str(pythonw) if pythonw.is_file() else str(exe)


def build_autostart_command(
    python_exe: Optional[str] = None,
    script_path: Optional[str] = None,
) -> str:
    """Kommandoraden för autostart: '"pythonw.exe" "folder.py"'."""
    script = Path(script_path or (Path(__file__).resolve().parent.parent
                                  / "folder.py"))
    return f'"{resolve_pythonw(python_exe)}" "{script}"'


def enable_autostart(
    script_path: Optional[str] = None,
    python_exe: Optional[str] = None,
    winreg_module: Optional[Any] = None,
) -> bool:
    """Slår PÅ autostart vid inloggning. True vid lyckad skrivning."""
    winreg = winreg_module or _winreg_module()
    if winreg is None:
        print("[Autostart] Endast Windows stöds — autostart avslagen.")
        return False
    command = build_autostart_command(python_exe, script_path)
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.SetValueEx(key, APP_VALUE_NAME, 0, winreg.REG_SZ, command)
        return True
    except Exception as exc:
        print(f"[Autostart] Kunde inte slå på autostart: {exc}")
        return False


def disable_autostart(winreg_module: Optional[Any] = None) -> bool:
    """Slår AV autostart (tar bort Run-värdet). True om det är borta."""
    winreg = winreg_module or _winreg_module()
    if winreg is None:
        print("[Autostart] Endast Windows stöds.")
        return False
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, APP_VALUE_NAME)
        return True
    except FileNotFoundError:
        return True  # redan borta = mål uppnått
    except Exception as exc:
        print(f"[Autostart] Kunde inte ta bort autostart: {exc}")
        return False


def is_autostart_enabled(winreg_module: Optional[Any] = None) -> bool:
    """True om autostart-värdet finns i registret."""
    winreg = winreg_module or _winreg_module()
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ
        ) as key:
            winreg.QueryValueEx(key, APP_VALUE_NAME)
        return True
    except Exception:
        # FileNotFoundError/OSError = värdet saknas; ALLT annat (t.ex.
        # ändrad API) får aldrig krascha appen vid start.
        return False


def get_autostart_command(winreg_module: Optional[Any] = None) -> Optional[str]:
    """Det sparade autostart-kommandot, eller None."""
    winreg = winreg_module or _winreg_module()
    if winreg is None:
        return None
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ
        ) as key:
            value, _type = winreg.QueryValueEx(key, APP_VALUE_NAME)
        return str(value)
    except Exception:
        return None


__all__ = [
    "RUN_KEY_PATH", "APP_VALUE_NAME",
    "resolve_pythonw", "build_autostart_command",
    "enable_autostart", "disable_autostart",
    "is_autostart_enabled", "get_autostart_command",
]
