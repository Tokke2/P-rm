"""Pure layout calculations shared by the Tk UI and headless tests."""

from __future__ import annotations

import re
from typing import Tuple


def compute_window_geometry(
    screen_width: int, screen_height: int, saved_geometry: str = ""
) -> Tuple[str, int, int]:
    """Return geometry and minimum size, fitting a tall window to the screen.

    A previously chosen width is retained if possible; height always uses the
    available screen height so the app opens with controls visible and avoids
    stale/off-screen saved positions.
    """
    screen_width = max(480, int(screen_width))
    screen_height = max(360, int(screen_height))
    available_width = max(480, screen_width - 32)
    available_height = max(340, screen_height - 60)
    match = re.match(r"^(\d+)x\d+", str(saved_geometry))
    preferred_width = int(match.group(1)) if match else min(1120, available_width)
    window_width = min(
        available_width, max(min(680, available_width), preferred_width)
    )
    x = max(0, (screen_width - window_width) // 2)
    geometry = f"{window_width}x{available_height}+{x}+0"
    return geometry, min(680, window_width), min(420, available_height)


__all__ = ["compute_window_geometry"]
