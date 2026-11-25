# Fil: Script/logotyp.py — Logotyphantering (PDF / SVG / EPS / AI / raster)
# Plats: Script/logotyp.py
# © Copyright Rickard Längkvist {get_copyright_year()} - All rights reserved
#
# Denna modul är "single source of truth" för inläsning av logotyper.
# label.py och folder.py delegerar hit, så konverteringslogiken finns bara
# på ett ställe.
#
# Konverteringar använder, i prioritetsordning:
#   PDF  : PyMuPDF → Ghostscript → Inkscape → pdftoppm (poppler)
#   SVG  : Inkscape → cairosvg → PyMuPDF
#   EPS  : Ghostscript → Inkscape
#   AI   : samma som EPS
#   Övrigt: Pillow (PNG, JPG, BMP, GIF, TIFF, WEBP …)
#
# Inga tkinter-fönster öppnas här: GUI:t visar istället ett meddelande om
# load_and_resize_logo() returnerar None.

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Tuple

from PIL import Image

# === KONSTANTER ===
LOGO_MAX_WIDTH_MM = 50          # mm
DPI = 300
MM_TO_PIXELS = DPI / 25.4
SVG_EXPORT_DPI_FACTOR = 1.5     # lite överupplösning → skarpare utskrift
LOGO_MIN_TOP_MARGIN_PX = 5

RASTER_FORMATS = {
    ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".tif", ".webp",
}
VECTOR_FORMATS = {".pdf", ".svg", ".eps", ".ai"}
ALL_FORMATS = RASTER_FORMATS | VECTOR_FORMATS

PDF_FORMATS = {".pdf"}
SVG_FORMATS = {".svg"}
EPS_FORMATS = {".eps", ".ai"}

DEFAULT_LOGO_FOLDER = Path(__file__).parent.parent / "Logotyp"
DEFAULT_EXPORT_FOLDER = Path(__file__).parent.parent / "export"


# ──────────────────────────────────────────────────────────
# COPYRIGHT / EXPORTMAPP
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


def get_export_folder() -> Path:
    """Returnerar (och skapar vid behov) export-mappen i approten."""
    folder = DEFAULT_EXPORT_FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def get_export_path(filename: str) -> Path:
    """Returnerar <approt>/export/<filename>."""
    return get_export_folder() / filename


# ──────────────────────────────────────────────────────────
# HITTA EXTERNA VERKTYG / VALFRIA BIBLIOTEK
# ──────────────────────────────────────────────────────────

def _first_existing(candidates: List[Optional[str]]) -> Optional[str]:
    return next((p for p in candidates if p and os.path.isfile(p)), None)


def find_inkscape() -> Optional[str]:
    """Letar efter Inkscape i PATH och vanliga installationsplatser."""
    return _first_existing([
        shutil.which("inkscape"),
        r"C:\Program Files\Inkscape\bin\inkscape.exe",
        r"C:\Program Files\Inkscape\inkscape.exe",
        r"C:\Program Files (x86)\Inkscape\bin\inkscape.exe",
        "/usr/bin/inkscape",
        "/usr/local/bin/inkscape",
        "/snap/bin/inkscape",
        "/opt/homebrew/bin/inkscape",
        "/Applications/Inkscape.app/Contents/MacOS/inkscape",
    ])


def find_ghostscript() -> Optional[str]:
    """Letar efter Ghostscript (gs / gswin64c / gswin32c)."""
    candidates = [
        shutil.which("gs"),
        shutil.which("gswin64c"),
        shutil.which("gswin32c"),
    ]
    for base in (r"C:\Program Files\gs", r"C:\Program Files (x86)\gs"):
        if os.path.isdir(base):
            try:
                for folder in os.listdir(base):
                    for exe in ("gswin64c.exe", "gswin32c.exe", "gs.exe"):
                        candidates.append(
                            os.path.join(base, folder, "bin", exe)
                        )
            except OSError:
                pass
    candidates += ["/usr/bin/gs", "/usr/local/bin/gs", "/opt/homebrew/bin/gs"]
    return _first_existing(candidates)


def find_pdftoppm() -> Optional[str]:
    """Letar efter pdftoppm från poppler (extra fallback för PDF)."""
    return _first_existing([
        shutil.which("pdftoppm"),
        shutil.which("pdftoppm.exe"),
        "/usr/bin/pdftoppm",
        "/opt/homebrew/bin/pdftoppm",
    ])


def _pymupdf_module() -> Any:
    """Returnerar PyMuPDF om det är installerat, annars None."""
    try:
        import pymupdf as mod  # PyMuPDF >= 1.24
        return mod
    except ImportError:
        pass
    try:
        import fitz as mod  # äldre namn
        return mod
    except ImportError:
        return None


def _cairosvg_module() -> Any:
    """Returnerar cairosvg om det går att importera, annars None."""
    try:
        import cairosvg
        return cairosvg
    except Exception:  # cairosvg behöver libcairo som kan saknas
        return None


def check_tools() -> dict:
    """Returnerar en översikt över tillgängliga konverteringsverktyg."""
    return {
        "inkscape": bool(find_inkscape()),
        "ghostscript": bool(find_ghostscript()),
        "pdftoppm": bool(find_pdftoppm()),
        "pymupdf": bool(_pymupdf_module()),
        "cairosvg": bool(_cairosvg_module()),
    }


# ──────────────────────────────────────────────────────────
# HJÄLPFUNKTIONER FÖR KONVERTERING
# ──────────────────────────────────────────────────────────

def _new_temp_png() -> str:
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    handle.close()
    return handle.name


def _remove(path: Optional[str]) -> None:
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


def _run(command: List[str], timeout: int = 120) -> bool:
    """Kör ett externt kommando och returnerar True vid noll exitkod."""
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()[:400]
            print(f"[Konvertering] Kommando misslyckades: {detail}")
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"[Konvertering] Kunde inte köra {command[0]}: {exc}")
        return False


def _trim_whitespace(img: Image.Image) -> Image.Image:
    """Tar bort tomma marginaler runt en konverterad vektorlogotyp.

    Transparens används när den finns, annars vit bakgrund. En liten
    marginal (2 px) lämnas kvar så att tunna linjer inte klipps bort.
    """
    if img.width < 4 or img.height < 4:
        return img

    rgba = img.convert("RGBA")
    alpha = rgba.getchannel("A")
    if alpha.getextrema()[0] < 250:
        # Genomskinlig (eller delvis genomskinlig) bakgrund.
        mask = alpha.point(lambda value: 255 if value > 8 else 0)
    else:
        # Opaque vit bakgrund: allt som inte är nära vitt är innehåll.
        mask = rgba.convert("L").point(lambda value: 255 if value < 250 else 0)

    bbox = mask.getbbox()
    if not bbox:
        return img

    pad = 2
    left = max(0, bbox[0] - pad)
    top = max(0, bbox[1] - pad)
    right = min(img.width, bbox[2] + pad)
    bottom = min(img.height, bbox[3] + pad)

    # Kräpp inte bort en stor del av motivet pga. enstaka pixlar.
    if right - left < img.width * 0.2 or bottom - top < img.height * 0.05:
        return img
    return img.crop((left, top, right, bottom))


def _resize_to_width(img: Image.Image, target_px: int) -> Image.Image:
    """Skalar bilden exakt till target_px bredd, bibehåller proportioner."""
    if target_px <= 0 or img.width == target_px:
        return img
    ratio = target_px / float(img.width)
    size = (max(1, int(round(img.width * ratio))),
            max(1, int(round(img.height * ratio))))
    try:
        resample = Image.Resampling.LANCZOS
    except AttributeError:  # Pillow < 9.1
        resample = Image.LANCZOS
    return img.resize(size, resample)


def _load_converted_png(path: str, target_px: int) -> Optional[Image.Image]:
    """Öppnar en konverterad PNG, beskär tomma marginaler och skalar."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return None
    try:
        with Image.open(path) as source:
            img = source.convert("RGBA")
            img.load()
        img = _trim_whitespace(img)
        img = _resize_to_width(img, target_px)
        return img
    except Exception as exc:
        print(f"[Logo] Kunde inte läsa konverterad bild: {exc}")
        return None


def _render_with_pymupdf(
    source: Path,
    output_path: str,
    width_px: int,
    *,
    svg: bool = False,
) -> bool:
    """Renderar första sidan i en PDF (eller en SVG) med PyMuPDF."""
    mod = _pymupdf_module()
    if mod is None:
        return False
    try:
        if svg:
            doc = mod.open(stream=source.read_bytes(), filetype="svg")
            pdf_bytes = doc.convert_to_pdf()
            doc = mod.open(stream=pdf_bytes, filetype="pdf")
        else:
            doc = mod.open(str(source))

        if doc.page_count < 1:
            return False
        page = doc.load_page(0)
        page_width = page.rect.width or 1.0
        scale = min(max(width_px / page_width, 0.05), 30.0)
        pixmap = page.get_pixmap(
            matrix=mod.Matrix(scale, scale), alpha=True, annots=False
        )
        pixmap.save(output_path)
        doc.close()
        return os.path.getsize(output_path) > 0
    except Exception as exc:
        print(f"[PyMuPDF] Konvertering misslyckades: {exc}")
        return False


def _inkscape_export(
    source: str,
    output_path: str,
    width_px: int,
    *,
    area_drawing: bool = False,
) -> bool:
    """Exporterar PNG med Inkscape (både 0.x och 1.x stöds)."""
    inkscape = find_inkscape()
    if not inkscape:
        return False
    try:
        version = subprocess.run(
            [inkscape, "--version"], capture_output=True, text=True, timeout=10
        )
        legacy = "0." in (version.stdout or "")
    except Exception:
        legacy = False

    if legacy:
        command = [
            inkscape, "--export-png", output_path,
            "--export-width", str(width_px),
            "--export-background-opacity", "0", source,
        ]
    else:
        command = [
            inkscape, source,
            f"--export-filename={output_path}",
            f"--export-width={width_px}",
            "--export-background-opacity=0",
        ]
        if area_drawing:
            command.append("--export-area-drawing")

    return _run(command) and os.path.exists(output_path) and os.path.getsize(output_path) > 0


# ──────────────────────────────────────────────────────────
# KONVERTERINGAR → PNG (temporära filer)
# ──────────────────────────────────────────────────────────

def convert_pdf_to_png(pdf_path: str, width_px: int) -> Optional[str]:
    """Konverterar första PDF-sidan till en temporär PNG-fil.

    Flera fallbackar: PyMuPDF, Ghostscript, Inkscape och pdftoppm.
    Returnerar sökvägen till PNG-filen eller None.
    """
    source = Path(pdf_path)
    if not source.is_file():
        return None

    # 1) PyMuPDF — snabbast och kräver inga externa program.
    out = _new_temp_png()
    if _render_with_pymupdf(source, out, width_px):
        print(f"[PDF] ✓ Konverterad med PyMuPDF ({width_px} px)")
        return out
    _remove(out)

    # 2) Ghostscript — renderar med transparent bakgrund.
    gs = find_ghostscript()
    if gs:
        out = _new_temp_png()
        command = [
            gs, "-dSAFER", "-dBATCH", "-dNOPAUSE", "-dQUIET",
            "-dFirstPage=1", "-dLastPage=1", "-dUseCropBox",
            "-dTextAlphaBits=4", "-dGraphicsAlphaBits=4",
            "-sDEVICE=pngalpha", "-r300",
            f"-sOutputFile={out}", str(source),
        ]
        if _run(command) and os.path.exists(out) and os.path.getsize(out) > 0:
            print("[PDF] ✓ Konverterad med Ghostscript")
            return out
        _remove(out)

    # 3) Inkscape.
    out = _new_temp_png()
    if _inkscape_export(str(source), out, width_px, area_drawing=True):
        print("[PDF] ✓ Konverterad med Inkscape")
        return out
    _remove(out)

    # 4) pdftoppm (poppler). Skriver till <prefix>.png, ej till prefixet.
    pdftoppm = find_pdftoppm()
    if pdftoppm:
        prefix = _new_temp_png()[:-4]
        output_path = prefix + ".png"
        command = [
            pdftoppm, "-png", "-r", "300", "-f", "1", "-l", "1",
            "-singlefile", str(source), prefix,
        ]
        if _run(command) and os.path.exists(output_path):
            print("[PDF] ✓ Konverterad med pdftoppm")
            return output_path
        _remove(output_path)

    print(
        "[PDF] ✗ Kunde inte läsa PDF-logotypen. Installera PyMuPDF "
        "(pip install pymupdf), Ghostscript, Inkscape eller poppler."
    )
    return None


def convert_svg_to_png(svg_path: str, width_px: int) -> Optional[str]:
    """Konverterar SVG till en temporär PNG-fil med transparent bakgrund."""
    source = Path(svg_path)
    if not source.is_file():
        return None

    # 1) Inkscape.
    out = _new_temp_png()
    if _inkscape_export(str(source), out, width_px):
        print(f"[SVG] ✓ Konverterad med Inkscape ({width_px} px)")
        return out
    _remove(out)

    # 2) cairosvg.
    cairosvg = _cairosvg_module()
    if cairosvg:
        out = _new_temp_png()
        try:
            cairosvg.svg2png(
                url=str(source), write_to=out, output_width=width_px
            )
            if os.path.exists(out) and os.path.getsize(out) > 0:
                print(f"[SVG] ✓ Konverterad med cairosvg ({width_px} px)")
                return out
        except Exception as exc:
            print(f"[SVG] cairosvg misslyckades: {exc}")
        _remove(out)

    # 3) PyMuPDF kan läsa SVG via konvertering till PDF.
    out = _new_temp_png()
    if _render_with_pymupdf(source, out, width_px, svg=True):
        print(f"[SVG] ✓ Konverterad med PyMuPDF ({width_px} px)")
        return out
    _remove(out)

    print(
        "[SVG] ✗ Kunde inte läsa SVG-logotypen. Installera Inkscape, "
        "cairosvg (pip install cairosvg) eller PyMuPDF."
    )
    return None


def convert_eps_to_png(eps_path: str, width_px: int) -> Optional[str]:
    """Konverterar EPS/AI till en temporär PNG-fil."""
    source = str(eps_path)
    if not os.path.isfile(source):
        return None

    # 1) Ghostscript med EPSCrop så att tomma sidmarginaler försvinner.
    gs = find_ghostscript()
    if gs:
        out = _new_temp_png()
        command = [
            gs, "-dSAFER", "-dBATCH", "-dNOPAUSE", "-dQUIET", "-dEPSCrop",
            "-dTextAlphaBits=4", "-dGraphicsAlphaBits=4",
            "-sDEVICE=pngalpha", f"-r{max(150, width_px // 6)}",
            f"-sOutputFile={out}", source,
        ]
        if _run(command) and os.path.exists(out) and os.path.getsize(out) > 0:
            print("[EPS] ✓ Konverterad med Ghostscript")
            return out
        _remove(out)

    # 2) Inkscape.
    out = _new_temp_png()
    if _inkscape_export(source, out, width_px, area_drawing=True):
        print("[EPS] ✓ Konverterad med Inkscape")
        return out
    _remove(out)

    print(
        "[EPS] ✗ Kunde inte läsa EPS/AI-logotypen. Installera "
        "Ghostscript eller Inkscape."
    )
    return None


# ──────────────────────────────────────────────────────────
# FILVÄLJARE
# ──────────────────────────────────────────────────────────

def select_logo_file(parent: Any = None) -> Tuple[Optional[str], Optional[str]]:
    """Öppnar filväljaren. Returnerar (sökväg, 'vector'|'raster')."""
    from tkinter import filedialog  # importeras sent: modulen är GUI-oberoende

    initial_dir = (
        str(DEFAULT_LOGO_FOLDER) if DEFAULT_LOGO_FOLDER.exists() else None
    )
    filepath = filedialog.askopenfilename(
        parent=parent,
        title="Välj logotyp (PDF, SVG, EPS, PNG …)",
        initialdir=initial_dir,
        filetypes=[
            ("Vektor & bild",
             ("*.pdf", "*.svg", "*.eps", "*.ai", "*.png", "*.jpg",
              "*.jpeg", "*.webp", "*.bmp", "*.gif", "*.tiff", "*.tif")),
            ("PDF-filer", ("*.pdf",)),
            ("SVG-filer", ("*.svg",)),
            ("EPS-filer", ("*.eps", "*.ai")),
            ("Rasterbilder",
             ("*.png", "*.jpg", "*.jpeg", "*.webp", "*.bmp", "*.gif",
              "*.tiff", "*.tif")),
            ("Alla filer", ("*.*",)),
        ],
    )
    if not filepath or not os.path.isfile(filepath):
        return None, None

    ext = os.path.splitext(filepath)[1].lower()
    kind = "vector" if ext in VECTOR_FORMATS else "raster"
    print(f"[Filväljare] Vald: {os.path.basename(filepath)} ({kind})")
    return filepath, kind


# ──────────────────────────────────────────────────────────
# LADDA OCH SKALA LOGOTYP
# ──────────────────────────────────────────────────────────

def load_and_resize_logo(
    filepath: str,
    max_width_mm: float = LOGO_MAX_WIDTH_MM,
    dpi: int = DPI,
) -> Optional[Image.Image]:
    """Läser in en logotyp och skalar den till önskad bredd.

    Stöder PDF (första sidan), SVG, EPS/AI och alla format Pillow klarar
    av. Returnerar en PIL.RGBA-bild eller None om filen inte kunde läsas.
    """
    if not filepath or not os.path.isfile(filepath):
        print(f"[Logo] Filen finns inte: {filepath}")
        return None

    path = Path(filepath)
    ext = path.suffix.lower()
    oversampled_px = max(1, int(max_width_mm * (dpi / 25.4) * SVG_EXPORT_DPI_FACTOR))
    final_px = max(1, int(max_width_mm * (dpi / 25.4)))
    temp_file: Optional[str] = None

    try:
        if ext in VECTOR_FORMATS:
            if ext in PDF_FORMATS:
                temp_file = convert_pdf_to_png(str(path), oversampled_px)
            elif ext in SVG_FORMATS:
                temp_file = convert_svg_to_png(str(path), oversampled_px)
            else:
                temp_file = convert_eps_to_png(str(path), oversampled_px)
            if not temp_file:
                return None
            img = _load_converted_png(temp_file, final_px)
        else:
            with Image.open(path) as source:
                img = source.convert("RGBA")
                img.load()
            img = _resize_to_width(img, final_px)

        if img is None or img.width == 0 or img.height == 0:
            return None
        print(
            f"[Logo] ✓ {path.name}: {img.width}×{img.height} px "
            f"({ext or 'okänt format'})"
        )
        return img

    except Exception as exc:
        print(f"[Logo] ✗ Fel vid inläsning av {path.name}: {exc}")
        traceback.print_exc()
        return None
    finally:
        _remove(temp_file)


# ──────────────────────────────────────────────────────────
# LUMINANS — förslag #16: automatisk logotypkontrast
# ──────────────────────────────────────────────────────────

def estimate_luminance(img: Optional[Image.Image]) -> Optional[float]:
    """Uppskattar medelluminansen (0.0 = svart, 1.0 = vit) i en logotyp.

    Transparanta pixlar kompositeras mot vitt (som på papper). Returnerar
    None om bilden saknas eller är tom. Används för att automatiskt välja
    kontraståtgärder (t.ex. vit baksida bakom mörka logotyper).
    """
    if img is None:
        return None
    try:
        if img.width == 0 or img.height == 0:
            return None
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        # Komposit mot vitt (alphakanalen avgör genomskinlighet).
        background = Image.new("RGBA", img.size, (255, 255, 255, 255))
        composited = Image.alpha_composite(background, img)
        gray = composited.convert("L")
        histogram = gray.histogram()
        total = sum(histogram)
        if not total:
            return None
        weighted = sum(value * count for value, count in enumerate(histogram))
        return weighted / (total * 255.0)
    except Exception as exc:
        print(f"[Logo] Kunde inte beräkna luminans: {exc}")
        return None


# ──────────────────────────────────────────────────────────
# PLACERING / LISTNING
# ──────────────────────────────────────────────────────────

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
    """Returnerar (x, y) för en horisontellt centrerad logotyp.

    PDF-koordinater: origo nere till vänster, y ökar uppåt. `area_y` är
    områdets nedre kant och `area_y + area_height` den övre kanten.
    """
    x = max(area_x, area_x + (area_width - logo_w) / 2.0)
    top_edge = area_y + area_height

    if align_top:
        y = top_edge - min_top_margin - logo_h
    else:
        y = area_y + (area_height - logo_h) / 2.0
        y = min(y, top_edge - min_top_margin - logo_h)
    return x, max(area_y, y)


def list_logos_in_folder(folder: Optional[Path] = None) -> List[Path]:
    """Listar alla logotyper i mappen (inklusive PDF)."""
    target = Path(folder) if folder else DEFAULT_LOGO_FOLDER
    if not target.is_dir():
        return []
    return sorted(
        (p for p in target.iterdir()
         if p.is_file() and p.suffix.lower() in ALL_FORMATS),
        key=lambda p: p.name.lower(),
    )


__all__ = [
    "get_copyright_year",
    "get_copyright_notice",
    "get_export_folder",
    "get_export_path",
    "DEFAULT_EXPORT_FOLDER",
    "DEFAULT_LOGO_FOLDER",
    "find_inkscape",
    "find_ghostscript",
    "find_pdftoppm",
    "check_tools",
    "convert_pdf_to_png",
    "convert_svg_to_png",
    "convert_eps_to_png",
    "select_logo_file",
    "load_and_resize_logo",
    "estimate_luminance",
    "compute_centered_logo_position",
    "list_logos_in_folder",
    "RASTER_FORMATS",
    "VECTOR_FORMATS",
    "PDF_FORMATS",
    "ALL_FORMATS",
    "LOGO_MIN_TOP_MARGIN_PX",
    "LOGO_MAX_WIDTH_MM",
    "DPI",
    "MM_TO_PIXELS",
]


if __name__ == "__main__":
    print(f"\n{'=' * 60}")
    print("  Logotyp-modul — stöd för PDF, SVG, EPS, AI och raster")
    print(f"  {get_copyright_notice()}")
    print(f"{'=' * 60}")
    print(f"\nLogotypmapp: {DEFAULT_LOGO_FOLDER}")
    for logo in list_logos_in_folder():
        print(f"  • {logo.name}")
    print("\nTillgängliga konverteringsverktyg:")
    for name, available in check_tools().items():
        print(f"  {'✓' if available else '✗'} {name}")
