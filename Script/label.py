# Fil: label.py — Etikett-ritlogik med dynamisk anpassning av logotyp och text
# Plats: Script/label.py
# © Copyright Rickard Längkvist {get_copyright_year()} - All rights reserved
#
# Ritlogik för rygg-, index- och verifikatetiketter. Inläsning och
# konvertering av logotyper delegeras till Script/logotyp.py (single source
# of truth). De gamla funktionsnamnen finns kvar som tunna wrappers så att
# befintlig kod fortsätter att fungera.

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

try:
    from Script import logotyp as LogoModule
    from Script import streckkod as BarcodeModule
except ImportError:  # när filen körs direkt ur Script-mappen
    import logotyp as LogoModule  # type: ignore[no-redef]
    import streckkod as BarcodeModule  # type: ignore[no-redef]


# ──────────────────────────────────────────────────────────
# STANDARDVÄRDEN FÖR MARGINALER (pt)
# ──────────────────────────────────────────────────────────
DEFAULT_LOGO_SIDE_MARGIN = 2
DEFAULT_LOGO_TOP_MARGIN = 5
DEFAULT_TEXT_SIDE_MARGIN = 4
DEFAULT_TEXT_TOP_MARGIN = 4
DEFAULT_LOGO_TEXT_SPACING = 3
LOGO_MIN_TOP_MARGIN_PX = 5

# Dynamisk anpassning
LOGO_MAX_WIDTH_MM = 40 * mm
LOGO_MAX_HEIGHT_RATIO = 0.50
LOGO_MIN_HEIGHT_RATIO = 0.10
MIN_LOGO_HEIGHT_PT = 3 * mm
LABEL_LINE_SPACING_FACTOR = 1.12
LABEL_MIN_FONT_SIZE = 4.0
LABEL_MAX_FONT_SIZE = 32.0
LABEL_BORDER_COLOR = colors.black
LABEL_BORDER_WIDTH_PT = 0.3 * mm

# Streckkod i etikettens underkant (#2)
BARCODE_BAND_MAX = 9 * mm          # största bandhöjd som reserveras
BARCODE_TEXT_GAP = 2 * mm          # mellanrum text ↔ streckkodsband
BARCODE_BOTTOM_GAP = 1.5 * mm      # avstånd från etikettens nederkant

# Automatisk logotypkontrast (#16)
LOGO_CONTRAST_THRESHOLD = 0.55     # under detta värde anses logotypen mörk
LOGO_CONTRAST_PAD = 2.0            # pt vit kant runt logotypen

DPI = 300

DEFAULT_LOGO_FOLDER = Path(__file__).parent.parent / "Logotyp"
PROFILES_FOLDER = Path(__file__).parent.parent / "Profiler"
DEFAULT_EXPORT_FOLDER = Path(__file__).parent.parent / "export"

_FALLBACK_BOLD_FONT = "Helvetica-Bold"
_preferred_bold_font = _FALLBACK_BOLD_FONT


# ──────────────────────────────────────────────────────────
# COPYRIGHT / EXPORTMAPP
# ──────────────────────────────────────────────────────────

def get_copyright_year() -> int:
    return datetime.now().year


def get_copyright_notice() -> str:
    return (
        f"© Copyright Rickard Längkvist {get_copyright_year()} "
        f"- All rights reserved"
    )


def get_export_folder() -> Path:
    """Returnerar (och skapar) export-mappen."""
    folder = DEFAULT_EXPORT_FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def get_export_path(filename: str) -> Path:
    return get_export_folder() / filename


# ──────────────────────────────────────────────────────────
# TYPSNITT
# ──────────────────────────────────────────────────────────

def get_bold_font() -> str:
    """Returnerar det registrerade fetade typsnittet som ska användas."""
    if _preferred_bold_font in pdfmetrics.getRegisteredFontNames():
        return _preferred_bold_font
    return _FALLBACK_BOLD_FONT


def resolve_font_name(font_name: str) -> str:
    """Fallbackar till Helvetica om ett begärt typsnitt inte är registrerat."""
    if font_name in pdfmetrics.getRegisteredFontNames():
        return font_name
    if "bold" in font_name.lower():
        return _FALLBACK_BOLD_FONT
    return "Helvetica"


def register_preferred_bold_font() -> str:
    """Registrerar ett TTF-typsnitt om något lämpligt finns på systemet."""
    candidates = [
        Path(font) for font in (
            os.environ.get("P_RM_BOLD_FONT", ""),
            r"C:\Windows\Fonts\arialbd.ttf",
            "/usr/share/fonts/truetype/msttcorefonts/Arial_Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/Library/Fonts/Arial Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        ) if font
    ]
    for path in candidates:
        if not path.is_file():
            continue
        try:
            pdfmetrics.registerFont(TTFont("LabelBold", str(path)))
            global _preferred_bold_font
            _preferred_bold_font = "LabelBold"
            print(f"[Font] ✓ Registrerad: {path.name}")
            return _preferred_bold_font
        except Exception as exc:
            print(f"[Font] Kunde inte registrera {path.name}: {exc}")
    print("[Font] ⚠ Använder inbyggt Helvetica-Bold")
    return get_bold_font()


# ──────────────────────────────────────────────────────────
# INSTÄLLNINGAR (marginaler)
# ──────────────────────────────────────────────────────────

@dataclass
class MarginSettings:
    """Inställningar för marginaler — kan sparas som profil."""

    logo_side_margin: float = DEFAULT_LOGO_SIDE_MARGIN
    logo_top_margin: float = DEFAULT_LOGO_TOP_MARGIN
    text_side_margin: float = DEFAULT_TEXT_SIDE_MARGIN
    text_top_margin: float = DEFAULT_TEXT_TOP_MARGIN
    logo_text_spacing: float = DEFAULT_LOGO_TEXT_SPACING
    logo_max_height_ratio: float = LOGO_MAX_HEIGHT_RATIO
    logo_min_height_ratio: float = LOGO_MIN_HEIGHT_RATIO
    logo_min_top_margin: float = LOGO_MIN_TOP_MARGIN_PX
    min_font_size: float = LABEL_MIN_FONT_SIZE
    max_font_size: float = LABEL_MAX_FONT_SIZE
    line_spacing: float = LABEL_LINE_SPACING_FACTOR
    profile_name: str = "Standard"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MarginSettings":
        return cls(**{
            key: value for key, value in data.items()
            if key in cls.__dataclass_fields__
        })

    def save_to_file(self, filepath: Path) -> bool:
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as handle:
                json.dump(self.to_dict(), handle, indent=2, ensure_ascii=False)
            return True
        except OSError as exc:
            print(f"[Profil] Kunde inte spara: {exc}")
            return False

    @classmethod
    def load_from_file(cls, filepath: Path) -> Optional["MarginSettings"]:
        try:
            if not filepath.is_file():
                return None
            with open(filepath, "r", encoding="utf-8") as handle:
                return cls.from_dict(json.load(handle))
        except (OSError, ValueError, TypeError) as exc:
            print(f"[Profil] Kunde inte läsa: {exc}")
            return None


_current_settings = MarginSettings()


def get_current_settings() -> MarginSettings:
    return _current_settings


def set_current_settings(settings: MarginSettings) -> None:
    global _current_settings
    _current_settings = settings


def reset_to_defaults() -> MarginSettings:
    global _current_settings
    _current_settings = MarginSettings()
    return _current_settings


# Profilhantering finns kvar för bakåtkompatibilitet.
def list_profiles() -> List[Path]:
    if not PROFILES_FOLDER.is_dir():
        return []
    return sorted(PROFILES_FOLDER.glob("*.json"))


def save_profile(name: str, settings: Optional[MarginSettings] = None) -> bool:
    settings = settings or _current_settings
    safe = "".join(
        char for char in name if char.isalnum() or char in (" ", "-", "_")
    ).strip() or "profil"
    settings.profile_name = name
    return settings.save_to_file(PROFILES_FOLDER / f"{safe}.json")


def load_profile(name: str) -> Optional[MarginSettings]:
    safe = "".join(
        char for char in name if char.isalnum() or char in (" ", "-", "_")
    ).strip()
    settings = MarginSettings.load_from_file(PROFILES_FOLDER / f"{safe}.json")
    if settings:
        set_current_settings(settings)
    return settings


def delete_profile(name: str) -> bool:
    safe = "".join(
        char for char in name if char.isalnum() or char in (" ", "-", "_")
    ).strip()
    path = PROFILES_FOLDER / f"{safe}.json"
    try:
        if path.is_file():
            path.unlink()
            return True
        return False
    except OSError:
        return False


# ──────────────────────────────────────────────────────────
# DELEGERAD LOGOTYPHANTERING (bakåtkompatibla wrappers)
# ──────────────────────────────────────────────────────────

def find_inkscape() -> Optional[str]:
    return LogoModule.find_inkscape()


def find_ghostscript() -> Optional[str]:
    return LogoModule.find_ghostscript()


def find_pdftoppm() -> Optional[str]:
    return LogoModule.find_pdftoppm()


def check_tools() -> dict:
    return LogoModule.check_tools()


def convert_pdf_to_png(pdf_path: str, width_px: int) -> Optional[str]:
    return LogoModule.convert_pdf_to_png(pdf_path, width_px)


def convert_svg_to_png(svg_path: str, width_px: int) -> Optional[str]:
    return LogoModule.convert_svg_to_png(svg_path, width_px)


def convert_eps_to_png(eps_path: str, width_px: int) -> Optional[str]:
    return LogoModule.convert_eps_to_png(eps_path, width_px)


def select_logo_file() -> Tuple[Optional[str], Optional[str]]:
    return LogoModule.select_logo_file()


def load_and_resize_logo(
    filepath: str,
    max_width_mm: float = LOGO_MAX_WIDTH_MM / mm,
    dpi: int = DPI,
) -> Optional[Image.Image]:
    """Läser in logotyp; standardbredd 40 mm (mot 50 mm i logotyp.py)."""
    return LogoModule.load_and_resize_logo(filepath, max_width_mm, dpi)


def compute_centered_logo_position(
    logo_w: float,
    logo_h: float,
    area_x: float,
    area_y: float,
    area_width: float,
    area_height: float,
    min_top_margin: float = LOGO_MIN_TOP_MARGIN_PX,
    align_top: bool = True,
) -> Tuple[float, float]:
    return LogoModule.compute_centered_logo_position(
        logo_w, logo_h, area_x, area_y, area_width, area_height,
        min_top_margin, align_top,
    )


# ──────────────────────────────────────────────────────────
# TEXTHANTERING
# ──────────────────────────────────────────────────────────

def _break_text_into_lines(
    text_content: str,
    canvas: Canvas,
    font_name: str,
    font_size: float,
    max_width: float,
) -> List[str]:
    """Bryter texten i rader som får plats inom max_width."""
    if not text_content or not text_content.strip():
        return []
    max_width = max(max_width, 1.0)
    raw_lines = text_content.replace(" / ", "\n").splitlines()
    lines: List[str] = []

    for raw in raw_lines:
        if not raw.strip():
            lines.append("")
            continue
        current = ""
        for word in raw.split():
            candidate = f"{current} {word}".strip() if current else word
            if canvas.stringWidth(candidate, font_name, font_size) <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                if canvas.stringWidth(word, font_name, font_size) <= max_width:
                    current = word
                else:
                    # Ett mycket långt ord: bryt det tecken för tecken.
                    chunk = ""
                    for char in word:
                        test = chunk + char
                        if canvas.stringWidth(test, font_name, font_size) > max_width and chunk:
                            lines.append(chunk)
                            chunk = char
                        else:
                            chunk = test
                    current = chunk
        if current:
            lines.append(current)
    return lines


def _calculate_optimal_logo_size(
    image: Image.Image,
    label_width: float,
    label_height: float,
    text_line_count: int,
    font_size: float,
    settings: Optional[MarginSettings] = None,
) -> Tuple[float, float]:
    """Beräknar hur stor logotypen får vara på etiketten."""
    if image is None or image.width == 0 or image.height == 0:
        return 0.0, 0.0
    settings = settings or _current_settings

    aspect = image.height / image.width
    max_logo_width = label_width - 2 * settings.logo_side_margin
    max_logo_height = label_height * settings.logo_max_height_ratio

    if text_line_count > 0:
        text_height = font_size * settings.line_spacing * text_line_count
        minimum_top = max(settings.logo_top_margin, settings.logo_min_top_margin)
        available = (
            label_height - text_height - settings.logo_text_spacing
            - minimum_top - settings.text_top_margin
        )
        min_logo_height = label_height * settings.logo_min_height_ratio
        max_logo_height = max(min_logo_height, min(max_logo_height, available))

    logo_width = max(0.0, max_logo_width)
    logo_height = logo_width * aspect
    if logo_height > max_logo_height:
        logo_height = max_logo_height
        logo_width = logo_height / aspect

    if logo_height < MIN_LOGO_HEIGHT_PT or logo_width < MIN_LOGO_HEIGHT_PT:
        return 0.0, 0.0
    return logo_width, logo_height


# ──────────────────────────────────────────────────────────
# RITFUNKTIONER
# ──────────────────────────────────────────────────────────

def draw_logo_on_page(
    canvas: Canvas,
    image: Optional[Image.Image],
    label_type: str = "index",
) -> float:
    """Ritar logotypen centrerad högst upp på A4-sidan.

    Returnerar höjden som logotyp + toppmargin tar i anspråk (pt).
    """
    if not image or image.width == 0:
        return 0.0
    try:
        page_width, page_height = canvas._pagesize
    except AttributeError:
        return 0.0

    settings = _current_settings
    top_gap = max(settings.logo_top_margin, settings.logo_min_top_margin, 5)
    width_pt = min(LOGO_MAX_WIDTH_MM, page_width - 2 * top_gap)
    if width_pt <= 0:
        return 0.0
    height_pt = width_pt * image.height / image.width
    if height_pt > page_height - 2 * top_gap:
        height_pt = page_height - 2 * top_gap
        width_pt = height_pt * image.width / image.height

    x, y = compute_centered_logo_position(
        width_pt, height_pt, 0.0, 0.0, page_width, page_height,
        min_top_margin=top_gap, align_top=True,
    )
    try:
        canvas.drawImage(
            ImageReader(image), x, y, width_pt, height_pt, mask="auto"
        )
        return height_pt + top_gap
    except Exception as exc:
        print(f"[Logo] Fel vid ritning: {exc}")
        return 0.0


def corner_mark_lines(
    width: float,
    height: float,
    length: Optional[float] = None,
) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
    """Geometri för förstärkta hörnmarkeringar (förslag #22).

    Returnerar 8 linjer ((start), (slut)) — två L-formade markeringar per
    hörn, inskrivna i etikettens hörn. Ren funktion så att geometrin kan
    testas utan PDF.
    """
    if width <= 0 or height <= 0:
        return []
    if length is None:
        length = min(width, height) * 0.14
    length = max(4.0, min(length, 14.0))
    inset = 0.5  # halva linjebredden så markeringen ligger i hörnet
    lines: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []

    # Vänster/höger x och nedre/övre y för varje hörn.
    for x_edge in ((inset, inset + length), (width - inset, width - inset - length)):
        for y_edge in (
            (inset, inset + length), (height - inset, height - inset - length)
        ):
            x, x2 = x_edge
            y, y2 = y_edge
            lines.append(((x, y), (x2, y)))
            lines.append(((x, y), (x, y2)))
    return lines


def _draw_corner_marks(canvas: Canvas, width: float, height: float) -> None:
    """Ritar förstärkta hörnmarkeringar (L-formade) i etikettens hörn."""
    canvas.saveState()
    canvas.setStrokeColor(colors.black)
    canvas.setLineWidth(1.1)
    for (x1, y1), (x2, y2) in corner_mark_lines(width, height):
        canvas.line(x1, y1, x2, y2)
    canvas.restoreState()


# Fyll-läge (v1.10.0, användarönskemål): texten fyller alltid etiketten
# med 5 px marginal från kanterna och delas ALDRIG upp på flera rader.
FILL_TEXT_MARGIN_PT = 5.0     # "5px från kanterna" (pt ≈ px vid 72 dpi)
FILL_MAX_FONT_PT = 400.0      # vettig övre gräns för fyll-läget


def _fit_single_line(
    canvas: Canvas,
    text_content: str,
    font_name: str,
    avail_width: float,
    avail_height: float,
    line_spacing: float = 1.0,
) -> float:
    """Fontstorlek så att EN rad fyller utrymmet (aldrig radbruten).

    Bredd (5 px-marginalen inräknad av anroparen) och höjd bestämmer
    minsta: ``size = min(avail_width / bredd_vid_1pt, avail_height /
    line_spacing)``. stringWidth skalar linjärt med storleken.
    """
    text_content = (text_content or "").strip()
    if not text_content or avail_width <= 0 or avail_height <= 0:
        return 1.0
    width_at_1 = canvas.stringWidth(text_content, font_name, 1.0)
    if width_at_1 <= 0.0:
        return 1.0
    by_width = avail_width / width_at_1
    by_height = avail_height / max(0.01, line_spacing)
    return max(1.0, min(by_width, by_height, FILL_MAX_FONT_PT))


def draw_single_label(
    canvas: Canvas,
    x_pos: float,
    y_pos: float,
    width: float,
    height: float,
    text_content: str,
    prepared_logo_image: Optional[Image.Image] = None,
    base_font_name: str = "Helvetica-Bold",
    initial_font_size: float = 12.0,
    auto_shrink_text: bool = True,
    settings: Optional[MarginSettings] = None,
    barcode_text: Optional[str] = None,
    corner_marks: bool = False,
    logo_contrast: bool = False,
    fill_text: bool = False,
) -> None:
    """Ritar en etikett med ram, valfri logotyp och autoanpassad text.

    `fill_text=True` (v1.10.0): texten är alltid EN rad som fyller
    utrymmet med 5 px marginal från kanterna (FILL_TEXT_MARGIN_PT) —
    den krympas/växer tills den fyller, men delas aldrig upp.
    """
    if width <= 0 or height <= 0:
        return
    settings = settings or _current_settings
    font_name = resolve_font_name(base_font_name)

    canvas.saveState()
    canvas.translate(x_pos, y_pos)

    # Ram
    canvas.setStrokeColor(LABEL_BORDER_COLOR)
    canvas.setLineWidth(LABEL_BORDER_WIDTH_PT)
    canvas.rect(0, 0, width, height)

    # Förstärkta hörnmarkeringar (ritas efter ramen så de syns tydligt).
    if corner_marks:
        _draw_corner_marks(canvas, width, height)

    text_content = (text_content or "").strip()
    has_text = bool(text_content)
    max_text_width = max(1.0, width - 2 * settings.text_side_margin)
    font_size = min(
        max(initial_font_size, settings.min_font_size), settings.max_font_size
    )
    initial_lines: List[str] = []
    if has_text and not fill_text:
        # Fyll-läget (fill_text) bryter ALDRIG rader — hoppar över helt.
        canvas.setFont(font_name, font_size)
        initial_lines = _break_text_into_lines(
            text_content, canvas, font_name, font_size, max_text_width
        )
    # Antal textrader (fyll-läget = alltid exakt 1 rad).
    text_line_count = len(initial_lines) or (1 if has_text else 0)

    # Streckkod i underkanten (#2) — reserverar ett band nedtill.
    barcode_band = 0.0
    if barcode_text:
        try:
            barcode_band = min(BARCODE_BAND_MAX, height * 0.20)
        except (TypeError, ValueError):
            barcode_band = 0.0

    # Logotyp (centrerad, med minsta avstånd till övre kanten)
    logo_w = logo_h = 0.0
    y_text_top = height - settings.text_top_margin
    if prepared_logo_image:
        logo_w, logo_h = _calculate_optimal_logo_size(
            prepared_logo_image, width, height,
            text_line_count, font_size, settings,
        )
        if logo_w > 0 and logo_h > 0:
            try:
                area_x = settings.logo_side_margin
                area_width = width - 2 * settings.logo_side_margin
                minimum_top = max(
                    settings.logo_min_top_margin, settings.logo_top_margin
                )
                x_logo, y_logo = compute_centered_logo_position(
                    logo_w, logo_h, area_x, 0.0, area_width, height,
                    min_top_margin=minimum_top, align_top=True,
                )
                # Automatisk logotypkontrast (#16): mörk logotyp får en
                # vit, rundad baksida så den förblir tydlig.
                if logo_contrast:
                    luminance = LogoModule.estimate_luminance(
                        prepared_logo_image
                    )
                    if luminance is not None and luminance < LOGO_CONTRAST_THRESHOLD:
                        canvas.setFillColor(colors.white)
                        canvas.setStrokeColor(colors.white)
                        canvas.roundRect(
                            x_logo - LOGO_CONTRAST_PAD,
                            y_logo - LOGO_CONTRAST_PAD,
                            logo_w + 2 * LOGO_CONTRAST_PAD,
                            logo_h + 2 * LOGO_CONTRAST_PAD,
                            radius=2.0, stroke=1, fill=1,
                        )
                canvas.drawImage(
                    ImageReader(prepared_logo_image),
                    x_logo, y_logo, logo_w, logo_h, mask="auto",
                )
                y_text_top = y_logo - settings.logo_text_spacing
            except Exception as exc:
                print(f"[Etikett] Logotypfel: {exc}")

    if not has_text or not initial_lines:
        # Streckkoden ritas även utan text (t.ex. rena kodetiketter).
        if barcode_band:
            _draw_barcode_band(
                canvas, width, height, barcode_band, barcode_text
            )
        canvas.restoreState()
        return

    y_text_bottom = settings.text_top_margin
    if barcode_band:
        y_text_bottom += barcode_band + BARCODE_TEXT_GAP
    avail_height = max(0.0, y_text_top - y_text_bottom)

    if fill_text:
        # Fyll-läge (v1.10.0): EN rad som fyller utrymmet med 5 px
        # marginal från kanterna — texten delas ALDRIG upp.
        lines = [text_content]
        font_size = _fit_single_line(
            canvas, text_content, font_name,
            width - 2 * FILL_TEXT_MARGIN_PT, avail_height,
            settings.line_spacing,
        )
        canvas.setFont(font_name, font_size)
    else:
        lines = initial_lines
        # Krymp texten tills den får plats (både höjd och bredd).
        while auto_shrink_text and font_size > settings.min_font_size:
            total_height = font_size * settings.line_spacing * len(lines)
            widest = max(
                (canvas.stringWidth(line, font_name, font_size) for line in lines),
                default=0.0,
            )
            if total_height <= avail_height and widest <= max_text_width:
                break
            font_size -= 0.5
            canvas.setFont(font_name, font_size)
            candidate = _break_text_into_lines(
                text_content, canvas, font_name, font_size, max_text_width
            )
            if candidate:
                lines = candidate

        font_size = max(font_size, settings.min_font_size)
        canvas.setFont(font_name, font_size)
    line_height = font_size * settings.line_spacing
    total_text_height = line_height * len(lines)
    if total_text_height <= avail_height:
        y_start = y_text_bottom + (avail_height - total_text_height) / 2.0
    else:
        y_start = y_text_bottom

    for index, line in enumerate(lines):
        line_width = canvas.stringWidth(line, font_name, font_size)
        x = max(settings.text_side_margin, (width - line_width) / 2.0)
        y = y_start + (len(lines) - 1 - index) * line_height
        canvas.drawString(x, y, line)

    if barcode_band:
        _draw_barcode_band(canvas, width, height, barcode_band, barcode_text)

    canvas.restoreState()


def _draw_barcode_band(
    canvas: Canvas,
    width: float,
    height: float,
    band_height: float,
    barcode_text: Optional[str],
) -> None:
    """Ritar Code 128-B streckkodsband i etikettens underkant (#2)."""
    if not barcode_text or band_height <= 0:
        return
    inset = min(4.0, width * 0.08)
    bar_width = max(8.0, width - 2 * inset)
    bar_height = band_height - BARCODE_BOTTOM_GAP
    if bar_height <= 0:
        return
    BarcodeModule.draw_code128(
        canvas,
        (width - bar_width) / 2.0,
        BARCODE_BOTTOM_GAP,
        bar_width,
        bar_height,
        barcode_text,
        show_text=False,
    )


__all__ = [
    "get_copyright_year",
    "get_copyright_notice",
    "get_export_folder",
    "get_export_path",
    "DEFAULT_EXPORT_FOLDER",
    "get_bold_font",
    "resolve_font_name",
    "register_preferred_bold_font",
    "find_inkscape",
    "find_ghostscript",
    "find_pdftoppm",
    "check_tools",
    "convert_pdf_to_png",
    "convert_svg_to_png",
    "convert_eps_to_png",
    "select_logo_file",
    "load_and_resize_logo",
    "draw_logo_on_page",
    "draw_single_label",
    "corner_mark_lines",
    "compute_centered_logo_position",
    "MarginSettings",
    "get_current_settings",
    "set_current_settings",
    "reset_to_defaults",
    "list_profiles",
    "save_profile",
    "load_profile",
    "delete_profile",
    "DEFAULT_LOGO_FOLDER",
    "PROFILES_FOLDER",
    "A4",
    "mm",
]
