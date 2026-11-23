# Fil: logotyp.py — Logotyphantering med SVG/EPS-stöd
# Plats: Script/logotyp.py
# © Copyright Rickard Längkvist {get_copyright_year()} - All rights reserved
# Kopplas till: folder.py och Script/label.py
# Stöd för: SVG, EPS, PNG, JPG och andra bildformat

from __future__ import annotations

import os
import shutil
import tempfile
import subprocess
import traceback
from datetime import datetime
from typing import Optional, Tuple, List
from pathlib import Path
from PIL import Image
from tkinter import filedialog, messagebox

# === KONSTANTER ===
LOGO_MAX_WIDTH_MM = 50          # mm (utan enhet för flexibilitet)
DPI               = 300
MM_TO_PIXELS      = DPI / 25.4
SVG_EXPORT_DPI_FACTOR = 1.5

# Centrering / placering av logotyp
LOGO_MIN_TOP_MARGIN_PX = 5     # Minsta avstånd från toppen (i pixlar)

# Stödda format
RASTER_FORMATS = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.tif'}
VECTOR_FORMATS = {'.svg', '.eps', '.ai'}
ALL_FORMATS    = RASTER_FORMATS | VECTOR_FORMATS

# Standardmappar (relativt till Script-mappen)
DEFAULT_LOGO_FOLDER   = Path(__file__).parent.parent / "Logotyp"
DEFAULT_EXPORT_FOLDER = Path(__file__).parent.parent / "export"


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
    Returnerar full sökväg för en fil i export/-mappen.

    Args:
        filename: Filnamn (t.ex. "verifikat_2026.pdf")

    Returns:
        Path till <approt>/export/<filename>
    """
    return get_export_folder() / filename


# ──────────────────────────────────────────────────────────
# HITTA INKSCAPE
# ──────────────────────────────────────────────────────────

def find_inkscape() -> Optional[str]:
    """
    Letar efter Inkscape i PATH och vanliga installationsplatser.

    Returns:
        Sökväg till Inkscape-binären eller None.
    """
    locations = [
        shutil.which("inkscape"),
        # Windows
        r"C:\Program Files\Inkscape\bin\inkscape.exe",
        r"C:\Program Files\Inkscape\inkscape.exe",
        r"C:\Program Files (x86)\Inkscape\bin\inkscape.exe",
        r"C:\Program Files (x86)\Inkscape\inkscape.exe",
        # Linux
        "/usr/bin/inkscape",
        "/usr/local/bin/inkscape",
        "/snap/bin/inkscape",
        # macOS
        "/opt/homebrew/bin/inkscape",
        "/Applications/Inkscape.app/Contents/MacOS/inkscape",
        "/Applications/Inkscape.app/Contents/Resources/bin/inkscape",
    ]

    result = next((p for p in locations if p and os.path.isfile(p)), None)
    if result:
        print(f"[Inkscape] ✓ Hittad: {result}")
    return result


# ──────────────────────────────────────────────────────────
# HITTA GHOSTSCRIPT
# ──────────────────────────────────────────────────────────

def find_ghostscript() -> Optional[str]:
    """
    Letar efter Ghostscript i PATH och vanliga installationsplatser.

    Returns:
        Sökväg till Ghostscript-binären eller None.
    """
    locations = [
        shutil.which("gs"),
        shutil.which("gswin64c"),
        shutil.which("gswin32c"),
    ]

    # Sök dynamiskt i Program Files\gs (Windows)
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

    # Linux / macOS
    locations.extend([
        "/usr/bin/gs",
        "/usr/local/bin/gs",
        "/opt/homebrew/bin/gs",
    ])

    result = next((p for p in locations if p and os.path.isfile(p)), None)
    if result:
        print(f"[Ghostscript] ✓ Hittad: {result}")
    return result


# ──────────────────────────────────────────────────────────
# KONVERTERA SVG → PNG
# ──────────────────────────────────────────────────────────

def convert_svg_to_png(svg_path: str, width_px: int) -> Optional[str]:
    """
    Konverterar SVG till PNG via Inkscape.

    Args:
        svg_path:  Sökväg till SVG-filen.
        width_px:  Önskad bredd i pixlar.

    Returns:
        Sökväg till temporär PNG-fil eller None vid fel.
    """
    inkscape_path = find_inkscape()
    if not inkscape_path:
        print("[SVG] ✗ Inkscape hittades inte")
        messagebox.showwarning(
            "Inkscape saknas",
            "Inkscape behövs för att öppna SVG-filer.\n\n"
            "Ladda ner från: https://inkscape.org/release/"
        )
        return None

    try:
        temp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        temp_out.close()
        output_path = temp_out.name

        # Kontrollera Inkscape-version
        try:
            version_out = subprocess.run(
                [inkscape_path, "--version"],
                capture_output=True, text=True, timeout=10
            )
            legacy  = "0." in version_out.stdout
            version = "legacy (0.x)" if legacy else "modern (1.x+)"
            print(f"[SVG] Inkscape version: {version}")
        except Exception:
            legacy = False

        if legacy:
            cmd = [
                inkscape_path,
                "--export-png", output_path,
                "--export-width", str(width_px),
                "--export-background-opacity", "0",
                svg_path,
            ]
        else:
            cmd = [
                inkscape_path,
                svg_path,
                f"--export-filename={output_path}",
                f"--export-width={width_px}",
                "--export-background-opacity=0",
            ]

        print(f"[SVG] Konverterar: {os.path.basename(svg_path)}...")
        result = subprocess.run(cmd, capture_output=True, timeout=120)

        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print(f"[SVG] ✓ Konverterad till PNG ({width_px} px)")
            return output_path
        else:
            stderr = result.stderr.decode() if result.stderr else "Okänt fel"
            print(f"[SVG] ✗ Konvertering misslyckades: {stderr}")
            return None

    except subprocess.TimeoutExpired:
        print("[SVG] ✗ Timeout (>120 s)")
        return None
    except Exception as e:
        print(f"[SVG] ✗ Undantag: {e}")
        traceback.print_exc()
        return None


# ──────────────────────────────────────────────────────────
# KONVERTERA EPS → PNG
# ──────────────────────────────────────────────────────────

def convert_eps_to_png(eps_path: str, width_px: int) -> Optional[str]:
    """
    Konverterar EPS till PNG via Ghostscript (primärt) eller Inkscape.

    Args:
        eps_path:  Sökväg till EPS-filen.
        width_px:  Önskad bredd i pixlar.

    Returns:
        Sökväg till temporär PNG-fil eller None vid fel.
    """
    # ── Ghostscript (primärt) ──────────────────────────────
    gs_path = find_ghostscript()
    if gs_path:
        try:
            temp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            temp_out.close()
            output_path = temp_out.name

            target_dpi = max(150, int(width_px / 6))
            cmd = [
                gs_path,
                "-dSAFER", "-dBATCH", "-dNOPAUSE", "-dEPSCrop",
                "-sDEVICE=pngalpha",
                f"-r{target_dpi}",
                f"-sOutputFile={output_path}",
                eps_path,
            ]
            print("[EPS] Konverterar via Ghostscript...")
            subprocess.run(cmd, capture_output=True, timeout=120)

            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                print("[EPS] ✓ Konverterad via Ghostscript")
                return output_path
        except Exception as e:
            print(f"[EPS] Ghostscript-fel: {e}")

    # ── Inkscape (fallback) ────────────────────────────────
    inkscape_path = find_inkscape()
    if inkscape_path:
        try:
            temp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            temp_out.close()
            output_path = temp_out.name

            cmd = [
                inkscape_path,
                eps_path,
                f"--export-filename={output_path}",
                f"--export-width={width_px}",
                "--export-background-opacity=0",
            ]
            print("[EPS] Konverterar via Inkscape...")
            subprocess.run(cmd, capture_output=True, timeout=120)

            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                print("[EPS] ✓ Konverterad via Inkscape")
                return output_path
        except Exception as e:
            print(f"[EPS] Inkscape-fel: {e}")

    print("[EPS] ✗ Varken Ghostscript eller Inkscape hittades")
    messagebox.showwarning(
        "EPS-stöd saknas",
        "Ghostscript eller Inkscape behövs för EPS-filer.\n\n"
        "Ghostscript: https://ghostscript.com/releases/\n"
        "Inkscape:    https://inkscape.org/release/"
    )
    return None


# ──────────────────────────────────────────────────────────
# VÄLJA LOGOTYPFIL
# ──────────────────────────────────────────────────────────

def select_logo_file() -> Tuple[Optional[str], Optional[str]]:
    """
    Öppnar filväljare för logotyp i Logotyp-mappen.

    Returns:
        Tuple (sökväg, typ) där typ är "vector" eller "raster",
        eller (None, None) om ingen fil valdes.
    """
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
            ("Vektorbilder",  ("*.svg", "*.eps", "*.ai")),
            ("SVG-filer",     ("*.svg",)),
            ("EPS-filer",     ("*.eps",)),
            ("PNG-filer",     ("*.png",)),
            ("JPEG-filer",    ("*.jpg", "*.jpeg")),
            ("Alla filer",    ("*.*",)),
        ]
    )

    if not filepath or not os.path.isfile(filepath):
        return None, None

    ext      = os.path.splitext(filepath)[1].lower()
    filename = os.path.basename(filepath)

    if ext in VECTOR_FORMATS:
        print(f"[Filväljare] ✓ Vald: {filename} (vektor)")
        return filepath, "vector"
    elif ext in RASTER_FORMATS:
        print(f"[Filväljare] ✓ Vald: {filename} (raster)")
        return filepath, "raster"
    else:
        print(f"[Filväljare] ⚠ Okänt format: {ext}, försöker som raster")
        return filepath, "raster"


# ──────────────────────────────────────────────────────────
# LADDA OCH SKALA LOGOTYP
# ──────────────────────────────────────────────────────────

def load_and_resize_logo(
    filepath:      str,
    max_width_mm:  float = LOGO_MAX_WIDTH_MM,
    dpi:           int   = DPI,
) -> Optional[Image.Image]:
    """
    Laddar och skalar logotyp till optimal storlek.

    Stöder SVG (Inkscape), EPS (Ghostscript/Inkscape) och
    rasterformat (PIL direkt).

    Args:
        filepath:      Sökväg till bildfilen.
        max_width_mm:  Maximal bredd i mm.
        dpi:           Upplösning för konvertering.

    Returns:
        PIL.Image eller None vid fel.
    """
    if not os.path.isfile(filepath):
        print(f"[Logo] ✗ Filen finns inte: {filepath}")
        return None

    ext          = os.path.splitext(filepath)[1].lower()
    filename     = os.path.basename(filepath)
    target_pix   = int(max_width_mm * MM_TO_PIXELS * SVG_EXPORT_DPI_FACTOR)
    temp_file    = None

    try:
        if ext == ".svg":
            print(f"[Logo] SVG detekterad: {filename}")
            temp_file = convert_svg_to_png(filepath, target_pix)
            if not temp_file:
                return None
            img = Image.open(temp_file).convert("RGBA")

        elif ext in {".eps", ".ai"}:
            print(f"[Logo] EPS/AI detekterad: {filename}")
            temp_file = convert_eps_to_png(filepath, target_pix)
            if not temp_file:
                return None
            img = Image.open(temp_file).convert("RGBA")

        else:
            print(f"[Logo] Raster detekterad: {filename}")
            img = Image.open(filepath)
            if img.mode not in ("RGB", "RGBA", "L"):
                img = img.convert("RGBA")

        w_px, h_px = img.size
        print(f"[Logo] Original: {w_px}×{h_px} px")

        if w_px == 0 or h_px == 0:
            print("[Logo] ✗ Ogiltig bildstorlek!")
            return None

        # DYNAMISK SKALNING
        final_target = int(max_width_mm * MM_TO_PIXELS)
        if w_px != final_target:
            ratio = final_target / float(w_px)
            new_w = max(1, int(w_px * ratio))
            new_h = max(1, int(h_px * ratio))

            try:
                resample_filter = Image.Resampling.LANCZOS
            except AttributeError:
                resample_filter = Image.LANCZOS  # Pillow < 9.1

            img = img.resize((new_w, new_h), resample_filter)
            print(f"[Logo] ✓ Skalad: {w_px}×{h_px} → {new_w}×{new_h} px")

        return img

    except Exception as e:
        print(f"[Logo] ✗ Fel: {e}")
        traceback.print_exc()
        return None

    finally:
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass


# ──────────────────────────────────────────────────────────
# BERÄKNA CENTRERAD LOGOTYPPLACERING
# ──────────────────────────────────────────────────────────

def compute_centered_logo_position(
    logo_w:       float,
    logo_h:       float,
    area_x:       float,
    area_y:       float,
    area_width:   float,
    area_height:  float,
    min_top_margin: float = LOGO_MIN_TOP_MARGIN_PX,
    align_top:    bool  = True,
) -> Tuple[float, float]:
    """
    Beräknar (x, y) så att logotypen CENTRERAS horisontellt inom
    marginalen och placeras med minst `min_top_margin` från toppen.

    Koordinatsystemet följer PDF/reportlab: origo nere till vänster,
    y ökar uppåt.  `area_y` = nedre kant, `area_y + area_height` = övre kant.

    Args:
        logo_w, logo_h:            Logotypens bredd/höjd.
        area_x, area_y:            Områdets nedre vänstra hörn.
        area_width, area_height:   Områdets storlek.
        min_top_margin:            Minsta avstånd från övre kant.
        align_top:                 True = placera vid toppen,
                                   False = centrera vertikalt.

    Returns:
        (x, y) för logotypens nedre vänstra hörn.
    """
    # Horisontell centrering
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
# LISTA LOGOTYPER I MAPP
# ──────────────────────────────────────────────────────────

def list_logos_in_folder(folder: Optional[Path] = None) -> List[Path]:
    """
    Listar alla logotypfiler i angiven mapp.

    Args:
        folder: Mapp att söka i (default: Logotyp/).

    Returns:
        Sorterad lista med Path-objekt.
    """
    if folder is None:
        folder = DEFAULT_LOGO_FOLDER

    if not folder.exists():
        return []

    logos: List[Path] = []
    for ext in ALL_FORMATS:
        logos.extend(folder.glob(f"*{ext}"))
        logos.extend(folder.glob(f"*{ext.upper()}"))

    return sorted(set(logos))


# ──────────────────────────────────────────────────────────
# KONTROLLERA VERKTYG
# ──────────────────────────────────────────────────────────

def check_tools() -> dict:
    """
    Kontrollerar vilka externa verktyg som är installerade.

    Returns:
        {'inkscape': path|None, 'ghostscript': path|None}
    """
    return {
        "inkscape":    find_inkscape(),
        "ghostscript": find_ghostscript(),
    }


# ──────────────────────────────────────────────────────────
# EXPORTERADE SYMBOLER
# ──────────────────────────────────────────────────────────

__all__ = [
    # Copyright
    "get_copyright_year",
    "get_copyright_notice",
    # Export
    "get_export_folder",
    "get_export_path",
    "DEFAULT_EXPORT_FOLDER",
    # Verktyg
    "find_inkscape",
    "find_ghostscript",
    "check_tools",
    # Konvertering
    "convert_svg_to_png",
    "convert_eps_to_png",
    # Logotyp
    "select_logo_file",
    "load_and_resize_logo",
    "compute_centered_logo_position",
    "list_logos_in_folder",
    # Konstanter
    "DEFAULT_LOGO_FOLDER",
    "LOGO_MIN_TOP_MARGIN_PX",
    "RASTER_FORMATS",
    "VECTOR_FORMATS",
    "ALL_FORMATS",
]


# ──────────────────────────────────────────────────────────
# MODULTEST (körs direkt: python Script/logotyp.py)
# ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\n{'=' * 60}")
    print("  Logotyp-modul v2.0")
    print(f"  {get_copyright_notice()}")
    print(f"{'=' * 60}")

    # Export-mapp
    export_folder = get_export_folder()
    print(f"\n📤 Export-mapp: {export_folder}")
    print(f"   {'✓ Finns' if export_folder.exists() else '✗ Saknas (skapas automatiskt)'}")

    # Logotyp-mapp
    print(f"\n📁 Logotypmapp: {DEFAULT_LOGO_FOLDER}")
    if DEFAULT_LOGO_FOLDER.exists():
        print("   ✓ Finns")
        logos = list_logos_in_folder()
        if logos:
            print(f"\n📂 Logotyper ({len(logos)} st):")
            for logo in logos[:10]:
                ext = logo.suffix.lower()
                typ = "vektor" if ext in VECTOR_FORMATS else "raster"
                print(f"   • {logo.name} ({typ})")
            if len(logos) > 10:
                print(f"   ... och {len(logos) - 10} till")
        else:
            print("   ⚠ Inga logotyper hittades")
    else:
        print("   ✗ Finns inte")

    # Verktyg
    print("\n🔧 Installerade verktyg:")
    tools = check_tools()
    for name, path in tools.items():
        status = f"✓ {path}" if path else "✗ Ej hittad"
        print(f"   {name.capitalize()}: {status}")

    # Stödda format
    print("\n🖼️  Stödda format:")
    print(f"   Vektor: {', '.join(sorted(VECTOR_FORMATS))}")
    print(f"   Raster: {', '.join(sorted(RASTER_FORMATS))}")

    # Testa filväljare
    print(f"\n{'─' * 60}")
    print("Testar filväljare...")

    from tkinter import Tk
    root = Tk()
    root.withdraw()

    filepath, filetype = select_logo_file()
    if filepath:
        print(f"\n✓ Vald fil: {os.path.basename(filepath)} ({filetype})")
        img = load_and_resize_logo(filepath)
        if img:
            print(f"✓ Laddad: {img.size[0]}×{img.size[1]} px")
            print(f"✓ Format: {img.mode}")
            # Visa var en exporterad fil skulle hamna
            example_out = get_export_path("test_logo_export.png")
            print(f"✓ Exempelexport-sökväg: {example_out}")
        else:
            print("✗ Kunde inte ladda bilden")
    else:
        print("Ingen fil vald")

    root.destroy()

    print(f"\n{'=' * 60}")
    print("Modultest klart!")