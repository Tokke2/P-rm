# Fil: label.py — Etikett-ritlogik med DYNAMISK anpassning av logotyp och text
# Plats: Script/label.py
# © Copyright Rickard Längkvist {get_copyright_year()} - All rights reserved
# Stöd för: SVG, EPS, PNG, JPG och andra bildformat
# Kopplas till: folder.py och Script/logotyp.py
# NYA FUNKTIONER: Justerbara marginaler och profilsparning
#                 + Logotyp centreras inom marginalen, min 5 px från toppen
#                 + Export sparas i approtens undermapp 'export/'

from __future__ import annotations

import os
import json
import shutil
import tempfile
import subprocess
import traceback
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any
from pathlib import Path
from dataclasses import dataclass, asdict, field

from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.utils import ImageReader
from PIL import Image
from tkinter import filedialog, messagebox

# ──────────────────────────────────────────────────────────
# STANDARDVÄRDEN FÖR MARGINALER (pt)
# ──────────────────────────────────────────────────────────
DEFAULT_LOGO_SIDE_MARGIN  = 2      # pt – från sidorna
DEFAULT_LOGO_TOP_MARGIN   = 5      # pt – minst 5 px från toppen
DEFAULT_TEXT_SIDE_MARGIN  = 4      # pt
DEFAULT_TEXT_TOP_MARGIN   = 4      # pt
DEFAULT_LOGO_TEXT_SPACING = 3      # pt – mellanrum logotyp ↔ text
LOGO_MIN_TOP_MARGIN_PX    = 5      # Minsta avstånd från toppen (px/pt)

# ──────────────────────────────────────────────────────────
# KONSTANTER FÖR DYNAMISK ANPASSNING
# ──────────────────────────────────────────────────────────
LOGO_MAX_WIDTH_MM        = 40 * mm
LOGO_MAX_HEIGHT_RATIO    = 0.50    # Max 50 % av etiketthöjden
LOGO_MIN_HEIGHT_RATIO    = 0.10    # Min 10 % om logotyp finns
MIN_LOGO_HEIGHT_PT       = 3 * mm
LABEL_LINE_SPACING_FACTOR = 1.12
LABEL_MIN_FONT_SIZE      = 4.0
LABEL_MAX_FONT_SIZE      = 32.0
LABEL_BORDER_COLOR       = colors.black
LABEL_BORDER_WIDTH_PT    = 0.3 * mm

# DPI
DPI                  = 300
MM_TO_PIXELS         = DPI / 25.4
SVG_EXPORT_DPI_FACTOR = 1.5

# ──────────────────────────────────────────────────────────
# MAPPAR
# ──────────────────────────────────────────────────────────
DEFAULT_LOGO_FOLDER   = Path(__file__).parent.parent / "Logotyp"
PROFILES_FOLDER       = Path(__file__).parent.parent / "Profiler"
DEFAULT_PROFILE_FILE  = PROFILES_FOLDER / "default_profile.json"
DEFAULT_EXPORT_FOLDER = Path(__file__).parent.parent / "export"


# ──────────────────────────────────────────────────────────
# EXPORTMAPP
# ──────────────────────────────────────────────────────────

def get_export_folder() -> Path:
    """
    Returnerar sökväg till export/-mappen (applikationsrotens undermapp).

    Skapar mappen om den inte finns.

    Returns:
        Path till <approt>/export/
    """
    folder = DEFAULT_EXPORT_FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def get_export_path(filename: str) -> Path:
    """
    Returnerar full sökväg för en exportfil.

    Args:
        filename: Filnamn (t.ex. "rygg_smal_Titel.pdf")

    Returns:
        Path till <approt>/export/<filename>
    """
    return get_export_folder() / filename


# ──────────────────────────────────────────────────────────
# DATACLASS — Marginalinställningar
# ──────────────────────────────────────────────────────────

@dataclass
class MarginSettings:
    """Inställningar för marginaler — kan sparas som profil."""

    # Logotypmarginaler (pt)
    logo_side_margin:    float = DEFAULT_LOGO_SIDE_MARGIN
    logo_top_margin:     float = DEFAULT_LOGO_TOP_MARGIN

    # Textmarginaler (pt)
    text_side_margin:    float = DEFAULT_TEXT_SIDE_MARGIN
    text_top_margin:     float = DEFAULT_TEXT_TOP_MARGIN

    # Mellanrum
    logo_text_spacing:   float = DEFAULT_LOGO_TEXT_SPACING

    # Logotypstorlek
    logo_max_height_ratio: float = LOGO_MAX_HEIGHT_RATIO
    logo_min_height_ratio: float = LOGO_MIN_HEIGHT_RATIO

    # Minsta avstånd från toppen
    logo_min_top_margin: float = LOGO_MIN_TOP_MARGIN_PX

    # Textstorlek
    min_font_size:       float = LABEL_MIN_FONT_SIZE
    max_font_size:       float = LABEL_MAX_FONT_SIZE
    line_spacing:        float = LABEL_LINE_SPACING_FACTOR

    # Profilnamn
    profile_name:        str   = "Standard"

    def to_dict(self) -> Dict[str, Any]:
        """Konverterar till dict för JSON-sparning."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MarginSettings":
        """Skapar från dict."""
        return cls(**{
            k: v for k, v in data.items()
            if k in cls.__dataclass_fields__
        })

    def save_to_file(self, filepath: Path) -> bool:
        """Sparar profil till JSON-fil."""
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
            print(f"[Profil] ✓ Sparad: {filepath.name}")
            return True
        except Exception as e:
            print(f"[Profil] ✗ Kunde inte spara: {e}")
            return False

    @classmethod
    def load_from_file(cls, filepath: Path) -> Optional["MarginSettings"]:
        """Laddar profil från JSON-fil."""
        try:
            if not filepath.exists():
                return None
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"[Profil] ✓ Laddad: {filepath.name}")
            return cls.from_dict(data)
        except Exception as e:
            print(f"[Profil] ✗ Kunde inte ladda: {e}")
            return None


# ──────────────────────────────────────────────────────────
# GLOBAL INSTÄLLNINGSOBJEKT
# ──────────────────────────────────────────────────────────
_current_settings = MarginSettings()


def get_current_settings() -> MarginSettings:
    """Returnerar nuvarande marginalinställningar."""
    return _current_settings


def set_current_settings(settings: MarginSettings) -> None:
    """Sätter nuvarande marginalinställningar."""
    global _current_settings
    _current_settings = settings


def reset_to_defaults() -> MarginSettings:
    """Återställer till standardvärden."""
    global _current_settings
    _current_settings = MarginSettings()
    return _current_settings


# ──────────────────────────────────────────────────────────
# PROFILHANTERING  (* oanvänd enl. beslut — koden bevaras)
# ──────────────────────────────────────────────────────────

def list_profiles() -> List[Path]:
    """Listar alla sparade profiler."""
    if not PROFILES_FOLDER.exists():
        return []
    return sorted(PROFILES_FOLDER.glob("*.json"))


def save_profile(
    name: str,
    settings: Optional[MarginSettings] = None,
) -> bool:
    """Sparar nuvarande (eller angivna) inställningar som profil."""
    if settings is None:
        settings = _current_settings
    safe = "".join(
        c for c in name if c.isalnum() or c in (" ", "-", "_")
    ).strip() or "profil"
    settings.profile_name = name
    return settings.save_to_file(PROFILES_FOLDER / f"{safe}.json")


def load_profile(name: str) -> Optional[MarginSettings]:
    """Laddar en namngiven profil och sätter den som aktiv."""
    safe = "".join(
        c for c in name if c.isalnum() or c in (" ", "-", "_")
    ).strip()
    s = MarginSettings.load_from_file(PROFILES_FOLDER / f"{safe}.json")
    if s:
        set_current_settings(s)
    return s


def delete_profile(name: str) -> bool:
    """Raderar en profil."""
    safe = "".join(
        c for c in name if c.isalnum() or c in (" ", "-", "_")
    ).strip()
    fp = PROFILES_FOLDER / f"{safe}.json"
    try:
        if fp.exists():
            fp.unlink()
            print(f"[Profil] ✓ Raderad: {fp.name}")
            return True
        return False
    except Exception as e:
        print(f"[Profil] ✗ Kunde inte radera: {e}")
        return False


# ──────────────────────────────────────────────────────────
# COPYRIGHT
# ──────────────────────────────────────────────────────────

def get_copyright_year() -> int:
    """Returnerar aktuellt år för dynamisk copyright-text."""
    return datetime.now().year


def get_copyright_notice() -> str:
    """Returnerar komplett copyright-text med dynamiskt år."""
    return (
        f"© Copyright Rickard Längkvist {get_copyright_year()} "
        f"- All rights reserved"
    )


# ──────────────────────────────────────────────────────────
# HITTA INKSCAPE
# ──────────────────────────────────────────────────────────

def find_inkscape() -> Optional[str]:
    """Letar efter Inkscape i PATH och vanliga installationsplatser."""
    locations = [
        shutil.which("inkscape"),
        r"C:\Program Files\Inkscape\bin\inkscape.exe",
        r"C:\Program Files\Inkscape\inkscape.exe",
        r"C:\Program Files (x86)\Inkscape\bin\inkscape.exe",
        r"C:\Program Files (x86)\Inkscape\inkscape.exe",
        "/usr/bin/inkscape",
        "/usr/local/bin/inkscape",
        "/opt/homebrew/bin/inkscape",
        "/snap/bin/inkscape",
        "/Applications/Inkscape.app/Contents/MacOS/inkscape",
    ]
    return next((p for p in locations if p and os.path.isfile(p)), None)


# ──────────────────────────────────────────────────────────
# HITTA GHOSTSCRIPT
# ──────────────────────────────────────────────────────────

def find_ghostscript() -> Optional[str]:
    """Letar efter Ghostscript i PATH och vanliga installationsplatser."""
    locations = [
        shutil.which("gs"),
        shutil.which("gswin64c"),
        shutil.which("gswin32c"),
    ]
    for base in [r"C:\Program Files\gs", r"C:\Program Files (x86)\gs"]:
        if os.path.isdir(base):
            try:
                for folder in os.listdir(base):
                    for exe in ["gswin64c.exe", "gswin32c.exe", "gs.exe"]:
                        path = os.path.join(base, folder, "bin", exe)
                        if os.path.isfile(path):
                            locations.append(path)
            except Exception:
                pass
    locations.extend([
        "/usr/bin/gs",
        "/usr/local/bin/gs",
        "/opt/homebrew/bin/gs",
    ])
    return next((p for p in locations if p and os.path.isfile(p)), None)


# ──────────────────────────────────────────────────────────
# KONVERTERA SVG → PNG
# ──────────────────────────────────────────────────────────

def convert_svg_to_png(svg_path: str, width_px: int) -> Optional[str]:
    """Konverterar SVG till PNG via Inkscape."""
    inkscape_path = find_inkscape()
    if not inkscape_path:
        print("[SVG] Inkscape hittades inte.")
        messagebox.showwarning(
            "Inkscape saknas",
            "Inkscape behövs för SVG-filer.\n\n"
            "Ladda ner: https://inkscape.org/release/"
        )
        return None

    try:
        temp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        temp_out.close()
        output_path = temp_out.name

        try:
            v = subprocess.run(
                [inkscape_path, "--version"],
                capture_output=True, text=True, timeout=10
            )
            legacy = "0." in v.stdout
        except Exception:
            legacy = False

        cmd = (
            [inkscape_path, "--export-png", output_path,
             "--export-width", str(width_px),
             "--export-background-opacity", "0", svg_path]
            if legacy else
            [inkscape_path, svg_path,
             f"--export-filename={output_path}",
             f"--export-width={width_px}",
             "--export-background-opacity=0"]
        )

        print(f"[SVG] Konverterar: {os.path.basename(svg_path)}")
        subprocess.run(cmd, capture_output=True, timeout=120)

        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print(f"[SVG] ✓ Konverterad ({width_px} px)")
            return output_path
        return None

    except Exception as e:
        print(f"[SVG] ✗ Fel: {e}")
        return None


# ──────────────────────────────────────────────────────────
# KONVERTERA EPS → PNG
# ──────────────────────────────────────────────────────────

def convert_eps_to_png(eps_path: str, width_px: int) -> Optional[str]:
    """Konverterar EPS till PNG via Ghostscript (primärt) eller Inkscape."""
    gs_path = find_ghostscript()
    if gs_path:
        try:
            temp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            temp_out.close()
            output_path = temp_out.name
            target_dpi  = max(150, int(width_px / 6))
            cmd = [
                gs_path, "-dSAFER", "-dBATCH", "-dNOPAUSE", "-dEPSCrop",
                "-sDEVICE=pngalpha", f"-r{target_dpi}",
                f"-sOutputFile={output_path}", eps_path,
            ]
            subprocess.run(cmd, capture_output=True, timeout=120)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                print("[EPS] ✓ Konverterad via Ghostscript")
                return output_path
        except Exception as e:
            print(f"[EPS] Ghostscript-fel: {e}")

    inkscape_path = find_inkscape()
    if inkscape_path:
        try:
            temp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            temp_out.close()
            output_path = temp_out.name
            cmd = [
                inkscape_path, eps_path,
                f"--export-filename={output_path}",
                f"--export-width={width_px}",
                "--export-background-opacity=0",
            ]
            subprocess.run(cmd, capture_output=True, timeout=120)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                print("[EPS] ✓ Konverterad via Inkscape")
                return output_path
        except Exception as e:
            print(f"[EPS] Inkscape-fel: {e}")

    messagebox.showwarning(
        "EPS-stöd saknas",
        "Ghostscript eller Inkscape behövs för EPS-filer."
    )
    return None


# ──────────────────────────────────────────────────────────
# VÄLJA LOGOTYPFIL
# ──────────────────────────────────────────────────────────

def select_logo_file() -> Tuple[Optional[str], Optional[str]]:
    """Öppnar filväljare för logotyp i Logotyp-mappen."""
    initial_dir = (
        str(DEFAULT_LOGO_FOLDER)
        if DEFAULT_LOGO_FOLDER.exists()
        else None
    )
    filepath = filedialog.askopenfilename(
        title="Välj logotyp (SVG, EPS, PNG, JPG...)",
        initialdir=initial_dir,
        filetypes=[
            ("Alla bilder",
             ("*.svg", "*.eps", "*.png", "*.jpg", "*.jpeg",
              "*.bmp", "*.gif", "*.tiff", "*.tif")),
            ("SVG-filer",  ("*.svg",)),
            ("EPS-filer",  ("*.eps",)),
            ("PNG-filer",  ("*.png",)),
            ("JPEG-filer", ("*.jpg", "*.jpeg")),
            ("Alla filer", ("*.*",)),
        ]
    )
    if not filepath or not os.path.isfile(filepath):
        return None, None

    ext = os.path.splitext(filepath)[1].lower()
    print(f"[Filväljare] Vald: {os.path.basename(filepath)}")
    return (filepath, "vector") if ext in {".svg", ".eps", ".ai"} else (filepath, "raster")


# ──────────────────────────────────────────────────────────
# LADDA OCH SKALA LOGOTYP
# ──────────────────────────────────────────────────────────

def load_and_resize_logo(
    filepath:     str,
    max_width_mm: float = LOGO_MAX_WIDTH_MM,
    dpi:          int   = DPI,
) -> Optional[Image.Image]:
    """DYNAMISK: Laddar och skalar logotyp till optimal storlek."""
    if not os.path.isfile(filepath):
        print(f"[Logo] Filen finns inte: {filepath}")
        return None

    ext          = os.path.splitext(filepath)[1].lower()
    target_pix   = int((max_width_mm / mm) / 25.4 * dpi * SVG_EXPORT_DPI_FACTOR)
    temp_file    = None

    try:
        if ext == ".svg":
            temp_file = convert_svg_to_png(filepath, target_pix)
            if not temp_file:
                return None
            img = Image.open(temp_file).convert("RGBA")

        elif ext in {".eps", ".ai"}:
            temp_file = convert_eps_to_png(filepath, target_pix)
            if not temp_file:
                return None
            img = Image.open(temp_file).convert("RGBA")

        else:
            img = Image.open(filepath)
            if img.mode not in ("RGB", "RGBA", "L"):
                img = img.convert("RGBA")

        w_px, h_px = img.size
        if w_px == 0 or h_px == 0:
            return None

        final_target = int((max_width_mm / mm) / 25.4 * dpi)
        if w_px != final_target:
            ratio = final_target / float(w_px)
            new_w = max(1, int(w_px * ratio))
            new_h = max(1, int(h_px * ratio))
            try:
                resample = Image.Resampling.LANCZOS
            except AttributeError:
                resample = Image.LANCZOS
            img = img.resize((new_w, new_h), resample)
            print(f"[Logo] ✓ Skalad: {w_px}×{h_px} → {new_w}×{new_h} px")

        return img

    except Exception as e:
        print(f"[Logo] ✗ Fel: {e}")
        return None

    finally:
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass


# ──────────────────────────────────────────────────────────
# CENTRERAD LOGOTYPPLACERING
# ──────────────────────────────────────────────────────────

def compute_centered_logo_position(
    logo_w:         float,
    logo_h:         float,
    area_x:         float,
    area_y:         float,
    area_width:     float,
    area_height:    float,
    min_top_margin: float = LOGO_MIN_TOP_MARGIN_PX,
    align_top:      bool  = True,
) -> Tuple[float, float]:
    """
    Beräknar (x, y) så att logotypen CENTRERAS horisontellt inom
    marginalen och placeras med minst `min_top_margin` från toppen.

    Koordinatsystem: PDF/reportlab (origo nere till vänster, y uppåt).
    `area_y` = nedre kant, `area_y + area_height` = övre kant.

    Returns:
        (x, y) för logotypens nedre vänstra hörn.
    """
    x = area_x + (area_width - logo_w) / 2.0
    if x < area_x:
        x = area_x

    top_edge = area_y + area_height

    if align_top:
        y = top_edge - min_top_margin - logo_h
    else:
        y     = area_y + (area_height - logo_h) / 2.0
        max_y = top_edge - min_top_margin - logo_h
        if y > max_y:
            y = max_y

    if y < area_y:
        y = area_y

    return x, y


# ──────────────────────────────────────────────────────────
# BERÄKNA OPTIMAL LOGOTYPSTORLEK (intern)
# ──────────────────────────────────────────────────────────

def _calculate_optimal_logo_size(
    image:           Image.Image,
    label_width:     float,
    label_height:    float,
    text_line_count: int,
    font_size:       float,
    settings:        Optional[MarginSettings] = None,
) -> Tuple[float, float]:
    """DYNAMISK: Beräknar optimal logotypstorlek med anpassade marginaler."""
    if not image or image.width == 0 or image.height == 0:
        return 0.0, 0.0

    if settings is None:
        settings = _current_settings

    aspect          = image.height / image.width
    max_logo_width  = label_width - 2 * settings.logo_side_margin
    max_logo_height = label_height * settings.logo_max_height_ratio

    if text_line_count > 0:
        line_height        = font_size * settings.line_spacing
        text_height        = line_height * text_line_count
        available_for_logo = (
            label_height - text_height
            - settings.logo_text_spacing
            - settings.logo_top_margin
            - settings.text_top_margin
        )
        min_logo_height = label_height * settings.logo_min_height_ratio
        max_logo_height = max(
            min_logo_height,
            min(max_logo_height, available_for_logo)
        )

    logo_w = max_logo_width
    logo_h = logo_w * aspect

    if logo_h > max_logo_height:
        logo_h = max_logo_height
        logo_w = logo_h / aspect

    if logo_h < MIN_LOGO_HEIGHT_PT or logo_w < MIN_LOGO_HEIGHT_PT:
        return 0.0, 0.0

    return max(logo_w, 0.0), max(logo_h, 0.0)


# ──────────────────────────────────────────────────────────
# BRYT TEXT I RADER (intern)
# ──────────────────────────────────────────────────────────

def _break_text_into_lines(
    text_content: str,
    canvas:       Canvas,
    font_name:    str,
    font_size:    float,
    max_width:    float,
) -> List[str]:
    """DYNAMISK: Bryter text i rader som ryms inom max_width."""
    if not text_content or not text_content.strip():
        return []

    raw_lines = text_content.replace(" / ", "\n").splitlines()
    lines: List[str] = []

    for line in raw_lines:
        if not line.strip():
            lines.append("")
            continue
        current_line = ""
        for word in line.split():
            test = (current_line + " " + word).strip() if current_line else word
            if canvas.stringWidth(test, font_name, font_size) <= max_width:
                current_line = test
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

    return lines


# ──────────────────────────────────────────────────────────
# RITA LOGOTYP PÅ A4-SIDA
# ──────────────────────────────────────────────────────────

def draw_logo_on_page(
    canvas:     Canvas,
    image:      Optional[Image.Image],
    label_type: str = "index",
) -> float:
    """
    DYNAMISK: Ritar logotypen högst upp på A4-sidan.

    Horisontellt centrerad, minst `logo_min_top_margin` (standard 15 mm)
    från toppen.

    Returns:
        Total höjd som logotypen + marginal tar upp (pt).
        Returnerar 0.0 om ingen logotyp eller fel.
    """
    if not image:
        return 0.0
    try:
        page_width, page_height = canvas._pagesize
    except AttributeError:
        return 0.0

    settings   = _current_settings
    width_pt   = LOGO_MAX_WIDTH_MM
    aspect     = image.height / image.width
    height_pt  = width_pt * aspect
    top_gap    = max(settings.logo_min_top_margin, 15 * mm)
    x          = (page_width - width_pt) / 2.0
    y          = page_height - height_pt - top_gap

    try:
        canvas.drawImage(
            ImageReader(image), x, y, width_pt, height_pt, mask="auto"
        )
        return height_pt + top_gap
    except Exception as e:
        print(f"[Logo] Fel vid ritning: {e}")
        return 0.0


# ──────────────────────────────────────────────────────────
# RITA ENSKILD ETIKETT
# ──────────────────────────────────────────────────────────

def draw_single_label(
    canvas:               Canvas,
    x_pos:                float,
    y_pos:                float,
    width:                float,
    height:               float,
    text_content:         str,
    prepared_logo_image:  Optional[Image.Image] = None,
    base_font_name:       str   = "Helvetica-Bold",
    initial_font_size:    float = 12.0,
    auto_shrink_text:     bool  = True,
    settings:             Optional[MarginSettings] = None,
) -> None:
    """
    DYNAMISK: Ritar en enskild etikett med ram, logotyp och autoanpassad text.

    Logotypen CENTRERAS horisontellt inom logo_side_margin och placeras
    minst `logo_min_top_margin` (5 pt) från toppen.

    Alla genererade PDF:er sparas via get_export_path() i export/-mappen.

    Args:
        canvas:              ReportLab Canvas.
        x_pos, y_pos:        Etikettens position (pt).
        width, height:       Etikettens storlek (pt).
        text_content:        Texten att visa.
        prepared_logo_image: Förberedd PIL.Image (eller None).
        base_font_name:      Fontnamn (Helvetica-Bold / Arial-Bold).
        initial_font_size:   Startfontstorlek (pt).
        auto_shrink_text:    Krymper text tills den får plats.
        settings:            Marginalinställningar (globala om None).
    """
    if width <= 0 or height <= 0:
        return

    if settings is None:
        settings = _current_settings

    canvas.saveState()
    canvas.translate(x_pos, y_pos)

    # ── Ram ───────────────────────────────────────────────
    canvas.setStrokeColor(LABEL_BORDER_COLOR)
    canvas.setLineWidth(LABEL_BORDER_WIDTH_PT)
    canvas.rect(0, 0, width, height)

    # ── Förbered text ─────────────────────────────────────
    text_content   = (text_content or "").strip()
    has_text       = bool(text_content)
    max_text_width = width - 2 * settings.text_side_margin
    font_size      = min(initial_font_size, settings.max_font_size)

    initial_lines: List[str] = []
    if has_text:
        canvas.setFont(base_font_name, font_size)
        initial_lines = _break_text_into_lines(
            text_content, canvas, base_font_name, font_size, max_text_width
        )

    # ── Logotyp (centrerad + min 5 pt topp) ───────────────
    logo_w, logo_h = 0.0, 0.0
    y_text_top     = height - settings.text_top_margin

    if prepared_logo_image:
        logo_w, logo_h = _calculate_optimal_logo_size(
            prepared_logo_image, width, height,
            len(initial_lines) if has_text else 0,
            font_size, settings,
        )

        if logo_w > 0 and logo_h > 0:
            try:
                area_x     = settings.logo_side_margin
                area_width = width - 2 * settings.logo_side_margin
                min_top    = max(
                    settings.logo_min_top_margin,
                    settings.logo_top_margin,
                )
                x_logo, y_logo = compute_centered_logo_position(
                    logo_w, logo_h,
                    area_x, 0.0, area_width, height,
                    min_top_margin=min_top,
                    align_top=True,
                )
                canvas.drawImage(
                    ImageReader(prepared_logo_image),
                    x_logo, y_logo, logo_w, logo_h,
                    mask="auto",
                )
                y_text_top = y_logo - settings.logo_text_spacing
            except Exception as e:
                print(f"[Etikett] Logotypfel: {e}")

    # ── Text ──────────────────────────────────────────────
    if not has_text or not initial_lines:
        canvas.restoreState()
        return

    y_text_bottom = settings.text_top_margin
    avail_height  = y_text_top - y_text_bottom
    lines         = initial_lines

    # DYNAMISK krympning
    while auto_shrink_text and font_size > settings.min_font_size:
        line_height    = font_size * settings.line_spacing
        total_height   = line_height * len(lines)
        max_line_width = max(
            (canvas.stringWidth(l, base_font_name, font_size) for l in lines),
            default=0.0,
        )
        if total_height <= avail_height and max_line_width <= max_text_width:
            break
        font_size -= 0.5
        canvas.setFont(base_font_name, font_size)
        lines = _break_text_into_lines(
            text_content, canvas, base_font_name, font_size, max_text_width
        )
        if not lines:
            continue

    font_size = max(font_size, settings.min_font_size)
    canvas.setFont(base_font_name, font_size)

    # Centrera text vertikalt i tillgängligt utrymme
    line_height       = font_size * settings.line_spacing
    total_text_height = line_height * len(lines)
    y_start           = y_text_bottom + (avail_height - total_text_height) / 2.0

    for i, line in enumerate(lines):
        line_width = canvas.stringWidth(line, base_font_name, font_size)
        x = max(settings.text_side_margin, (width - line_width) / 2.0)
        y = y_start + (len(lines) - 1 - i) * line_height
        canvas.drawString(x, y, line)

    canvas.restoreState()


# ──────────────────────────────────────────────────────────
# EXPORTERADE SYMBOLER
# ──────────────────────────────────────────────────────────

__all__ = [
    # Copyright
    "get_copyright_year",
    "get_copyright_notice",
    # Export-mapp
    "get_export_folder",
    "get_export_path",
    "DEFAULT_EXPORT_FOLDER",
    # Verktyg
    "find_inkscape",
    "find_ghostscript",
    # Filhantering
    "select_logo_file",
    "load_and_resize_logo",
    # Ritfunktioner
    "draw_logo_on_page",
    "draw_single_label",
    "compute_centered_logo_position",
    # Inställningar
    "MarginSettings",
    "get_current_settings",
    "set_current_settings",
    "reset_to_defaults",
    # Profiler (* oanvända enl. beslut — bevaras)
    "list_profiles",
    "save_profile",
    "load_profile",
    "delete_profile",
    # Mappar
    "DEFAULT_LOGO_FOLDER",
    "PROFILES_FOLDER",
]


# ──────────────────────────────────────────────────────────
# MODULTEST (python Script/label.py)
# ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\n{'=' * 60}")
    print(f"  {get_copyright_notice()}")
    print(f"{'=' * 60}")

    # Export-mapp
    export_folder = get_export_folder()
    print(f"\n📤 Export-mapp: {export_folder}")
    print(f"   {'✓ Finns' if export_folder.exists() else '✗ Saknas (skapas automatiskt)'}")

    # Exempelexportsökväg
    example = get_export_path("rygg_smal_Test.pdf")
    print(f"   Exempelsökväg: {example}")

    # Mappar
    print(f"\n📁 Mappar:")
    print(f"   Logotyper: {DEFAULT_LOGO_FOLDER}")
    print(f"   Profiler:  {PROFILES_FOLDER}")

    # Nuvarande inställningar
    print(f"\n⚙️  Nuvarande inställningar:")
    s = get_current_settings()
    print(f"   Logotypmarginal (sida): {s.logo_side_margin} pt")
    print(f"   Logotypmarginal (topp): {s.logo_top_margin} pt")
    print(f"   Logo min topp:          {s.logo_min_top_margin} pt")
    print(f"   Textmarginal (sida):    {s.text_side_margin} pt")
    print(f"   Textmarginal (topp):    {s.text_top_margin} pt")
    print(f"   Logo-text mellanrum:    {s.logo_text_spacing} pt")

    # Sparade profiler
    print(f"\n📋 Sparade profiler:")
    profiles = list_profiles()
    if profiles:
        for p in profiles:
            print(f"   • {p.stem}")
    else:
        print("   (inga profiler sparade)")

    # Verktyg
    print(f"\n🔧 Verktyg:")
    print(f"   Inkscape:    {'✓ Hittad' if find_inkscape()    else '✗ Ej hittad'}")
    print(f"   Ghostscript: {'✓ Hittad' if find_ghostscript() else '✗ Ej hittad'}")

    # Testa profilsparning
    print(f"\n{'─' * 60}")
    print("Testar profilsparning...")
    test_s = MarginSettings(
        logo_side_margin=5,
        logo_top_margin=5,
        text_side_margin=10,
        text_top_margin=10,
        profile_name="Test Profil",
    )
    if save_profile("Test Profil", test_s):
        print("✓ Profil 'Test Profil' sparad")
        loaded = load_profile("Test Profil")
        if loaded:
            print(f"✓ Profil laddad: {loaded.profile_name}")
            print(f"  Logo sidmarginal: {loaded.logo_side_margin} pt")

    print(f"\n{'=' * 60}")
    print("Modultest klart!")