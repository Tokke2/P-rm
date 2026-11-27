# Fil: Script/skarm.py — Skärm-/DPI-hantering (AGENTS.md §11)
#
# * DPI-medvetenhet på Windows (skarp text på hög-DPI-skärmar, ingen
#   grumlig skalning)
# * Tk-scaling enligt skärmens DPI
# * Startgeometri: fönstret startar i MAX HÖJD-läge (anpassat efter
#   skärmen minus taskbar), med anpassad bredd och centrerad placering
#
# Rena funktioner där det går — geometrilogiken är enhetstestbar utan
# Tk. Ingen GUI-kod skapas här (tkinter behövs bara vid anrop).

from __future__ import annotations

import re
import sys
from typing import Optional

TASKBAR_RESERVE = 72     # px reserverade för taskbar/systemrad
EDGE_MARGIN = 16         # marginal till skärmkanterna
MIN_WIDTH = 880          # matchar appens minsize
PREFERRED_RATIO = 0.62   # bredd = 62 % av skärmen om inget sparat värde
MAX_WIDTH = 1500


def enable_dpi_awareness() -> bool:
    """Gör processen DPI-medveten (Windows) — skarp rendering på 4K/skalning.

    Måste anropas FÖRE Tk-fönstret skapas. Returnerar True vid lyckad
    aktivering; no-op (False) på andra plattformar.
    """
    if not sys.platform.startswith("win"):
        return False
    try:
        import ctypes

        try:
            # Windows 10 1703+: per-monitor v2
            ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)
            return True
        except (AttributeError, OSError):
            pass
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor
            return True
        except (AttributeError, OSError):
            pass
        try:
            ctypes.windll.user32.SetProcessDPIAware()
            return True
        except (AttributeError, OSError):
            return False
    except Exception:
        return False


def parse_geometry(geometry: str) -> Optional[int]:
    """Plockar bredden ur en Tk-geometristräng 'WxH+X+Y' → W (eller None)."""
    match = re.match(r"^(\d+)x", str(geometry or "").strip())
    return int(match.group(1)) if match else None


def compute_start_geometry(
    screen_width: int,
    screen_height: int,
    saved_geometry: str = "",
    *,
    taskbar_reserve: int = TASKBAR_RESERVE,
    edge_margin: int = EDGE_MARGIN,
    min_width: int = MIN_WIDTH,
    preferred_ratio: float = PREFERRED_RATIO,
    max_width: int = MAX_WIDTH,
) -> str:
    """Beräknar startgeometri: max höjd, anpassad bredd, centrerad.

    * Höjd = skärmhöjd minus taskbar-reserv (aldrig under 600 px)
    * Bredd = sparat värde om det finns, annars preferred_ratio av skärmen,
      clampad till [min_width, min(max_width, skärm − 2·marginal)]
    * Placering: horisontellt centrerad, med liten toppmarginal
    """
    if screen_width <= 0 or screen_height <= 0:
        return "1024x720+80+40"

    height = max(600, screen_height - taskbar_reserve - edge_margin)

    saved_width = parse_geometry(saved_geometry)
    width = saved_width or int(screen_width * preferred_ratio)
    width_cap = min(max_width, screen_width - 2 * edge_margin)
    width = max(min(min_width, width_cap), min(width, width_cap))

    x = max(0, (screen_width - width) // 2)
    y = max(0, edge_margin // 2)
    return f"{width}x{height}+{x}+{y}"


def ensure_no_console_streams() -> bool:
    """Skyddar print vid start utan konsol (pythonw, §9).

    Windows startar pythonw.exe utan stdout/stderr — ett enda print()
    skulle då krascha appen (AttributeError). Denna funktion dirigerar
    None-strömmarna till devnull. Anropas FÖRST i main(). Returnerar
    True om någon ström behövde omdirigeras.
    """
    redirected = False
    import os

    for stream_name in ("stdout", "stderr"):
        if getattr(sys, stream_name) is None:
            setattr(
                sys, stream_name,
                open(os.devnull, "w", encoding="utf-8")
            )
            redirected = True
    return redirected


def apply_scaling(root: object) -> Optional[float]:
    """Sätter Tk-scaling efter skärmens DPI (tydligare, större text).

    Anropas efter att root skapats. Returnerar DPI eller None vid fel.
    """
    try:
        dpi = float(root.winfo_fpixels("1i"))  # type: ignore[attr-defined]
        if dpi > 0:
            root.tk.call("tk", "scaling", dpi / 72.0)  # type: ignore[attr-defined]
            return dpi
    except Exception:
        pass
    return None


def configure_fonts(root: object) -> None:
    """Skärper standardtypsnitt: Segoe UI + lite större storlek på Windows."""
    try:
        from tkinter import font as tkfont

        family = "Segoe UI" if sys.platform.startswith("win") else None
        for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont",
                     "TkHeadingFont", "TkTooltipFont"):
            try:
                named = tkfont.nametofont(name)
                if family:
                    named.configure(family=family, size=10)
                else:
                    named.configure(size=10)
            except Exception:
                continue
    except Exception:
        pass


__all__ = [
    "TASKBAR_RESERVE",
    "EDGE_MARGIN",
    "MIN_WIDTH",
    "PREFERRED_RATIO",
    "MAX_WIDTH",
    "enable_dpi_awareness",
    "ensure_no_console_streams",
    "parse_geometry",
    "compute_start_geometry",
    "apply_scaling",
    "configure_fonts",
]
