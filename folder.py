# Fil: folder.py — GUI för etikettgenerator med dynamisk anpassning
# © Copyright Rickard Längkvist {get_copyright_year()} - All rights reserved
# Stöd för logotyper i PDF, SVG, EPS, AI, PNG, JPG, TIFF m.fl.
# Kopplar ihop: Script/label.py, Script/logotyp.py, Script/verifikat.py
#               och Script/settings_store.py
# Export: PDF:er sparas i undermappen 'export/'

from __future__ import annotations

import os
import queue
import re
import subprocess
import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk
from typing import List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

# === Moduler i Script-mappen ===
try:
    from Script import label as LabelModule
    from Script import logotyp as LogoModule
    from Script import settings_store as SettingsModule
    from Script import verifikat as VerifikatModule
    from Script import arkivindex as ArkivindexModule
    from Script import streckkod as BarcodeModule
    from Script import loggar as LoggModule
    from Script import skarm as SkarmModule
    from Script import gui_helpers as GuiHelpersModule
    from Script import updater as UpdaterModule
except ImportError:
    import label as LabelModule            # type: ignore[no-redef]
    import logotyp as LogoModule            # type: ignore[no-redef]
    import settings_store as SettingsModule  # type: ignore[no-redef]
    import verifikat as VerifikatModule      # type: ignore[no-redef]
    import arkivindex as ArkivindexModule    # type: ignore[no-redef]
    import streckkod as BarcodeModule        # type: ignore[no-redef]
    import loggar as LoggModule              # type: ignore[no-redef]
    import skarm as SkarmModule              # type: ignore[no-redef]
    import gui_helpers as GuiHelpersModule   # type: ignore[no-redef]
    import updater as UpdaterModule          # type: ignore[no-redef]


# === Konstanter ===
BINDER_SMALL_WIDTH = 41 * mm
BINDER_THICK_WIDTH = 57 * mm
BINDER_HEIGHT = 64 * mm
PDF_SIDE_MARGIN = 10 * mm
PDF_TOP_MARGIN = 10 * mm
PDF_SPACING = 5 * mm
A4_WIDTH, A4_HEIGHT = A4

CUT_LINE_COLOR = colors.grey
CUT_LINE_WIDTH = 0.3
CUT_LINE_DASH = (2, 2)

MONTHS_SE = VerifikatModule.MONTHS_SE
DEFAULT_LOGO_FOLDER = Path(__file__).parent / "Logotyp"
ASSETS_FOLDER = Path(__file__).parent / "assets"
APP_LOGOTYP_SVG = ASSETS_FOLDER / "app_logotyp.svg"
APP_LOGOTYP_ICON = ASSETS_FOLDER / "app_logotyp_512.png"

VALID_LABEL_TYPES = {"rygg_smal", "rygg_tjock", "index"}


# ──────────────────────────────────────────────────────────
# HJÄLPFUNKTIONER
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


def _get_out_path(filename: str) -> Path:
    """Returnerar full sökväg till en PDF i export/-mappen."""
    return LabelModule.get_export_path(filename)


def _grid_size(width: float, height: float) -> tuple[int, int]:
    """Antal kolumner och rader som får plats på ett A4-ark."""
    return VerifikatModule.grid_size(
        width, height, A4, PDF_SIDE_MARGIN, PDF_TOP_MARGIN, PDF_SPACING
    )


def _bind_mousewheel(widget: tk.Widget) -> None:
    """Mushjulsscroll för just denna widget (och dess barn)."""
    def on_wheel(event) -> None:
        widget.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def on_button(event) -> None:
        widget.yview_scroll(-1 if event.num == 4 else 1, "units")

    widget.bind("<MouseWheel>", on_wheel)
    widget.bind("<Button-4>", on_button)
    widget.bind("<Button-5>", on_button)


def _create_root() -> tk.Tk:
    """Skapar huvudfönstret, med ttkthemes om det är installerat."""
    try:
        from ttkthemes import ThemedTk
        return ThemedTk(theme="arc")
    except Exception:
        return tk.Tk()


# ──────────────────────────────────────────────────────────
# GUI-KLASS
# ──────────────────────────────────────────────────────────

class LabelGUI:
    def __init__(self, root: tk.Tk, saved: Optional[dict] = None):
        self.root = root
        self.saved = dict(saved) if saved is not None else SettingsModule.load_settings()
        self.root.title(f"Pärmetikett Generator {get_copyright_year()}")
        # §11: fönstret startar i MAX HÖJD-läge (anpassat efter skärmen)
        # med anpassad bredd (sparminnad bredd används om den fanns).
        self.root.geometry(SkarmModule.compute_start_geometry(
            self.root.winfo_screenwidth(),
            self.root.winfo_screenheight(),
            self.saved.get("window_geometry", ""),
        ))
        self.root.minsize(880, 620)

        # ── Tkinter-variabler (värden från settings.json) ──
        saved_type = self.saved.get("label_type", "rygg_smal")
        self.type_var = tk.StringVar(
            value=saved_type if saved_type in VALID_LABEL_TYPES else "rygg_smal"
        )
        self.auto_shrink = tk.BooleanVar(value=bool(self.saved.get("auto_shrink", True)))
        self.multi_label = tk.BooleanVar(value=bool(self.saved.get("multi_label", False)))
        self.cut_lines_var = tk.BooleanVar(value=bool(self.saved.get("cut_lines", True)))

        self.text_size_var = tk.IntVar(
            value=self._clamp(self.saved.get("text_size", 16), 8, 32)
        )
        self.antal_var = tk.IntVar(
            value=self._clamp(self.saved.get("label_count", 1), 1, 50)
        )

        saved_year = self._clamp(
            self.saved.get("verifikat_year", 0), 0, VerifikatModule.MAX_YEAR
        )
        self.verifikat_year_var = tk.IntVar(
            value=saved_year or get_copyright_year()
        )
        self.verifikat_per_month_var = tk.IntVar(
            value=self._clamp(
                self.saved.get("verifikat_per_month", 2),
                VerifikatModule.MIN_PER_MONTH,
                VerifikatModule.MAX_PER_MONTH,
            )
        )

        # Förslag #10/#11: periodläge (manad/kvartal/halvar) och språk.
        saved_period = str(self.saved.get("verifikat_period", "manad"))
        self.verifikat_period_var = tk.StringVar(
            value=saved_period if saved_period in VerifikatModule.PERIOD_MODES
            else VerifikatModule.DEFAULT_PERIOD
        )
        saved_language = str(self.saved.get("verifikat_language", "se"))
        self.verifikat_language_var = tk.StringVar(
            value=saved_language if saved_language in VerifikatModule.MONTHS_BY_LANGUAGE
            else VerifikatModule.DEFAULT_LANGUAGE
        )

        # Förslag #2/#22/#16: streckkod, hörnmarkeringar, logotypkontrast.
        self.barcode_var = tk.BooleanVar(
            value=bool(self.saved.get("barcode_labels", False))
        )
        self.corner_marks_var = tk.BooleanVar(
            value=bool(self.saved.get("corner_marks", False))
        )
        self.logo_contrast_var = tk.BooleanVar(
            value=bool(self.saved.get("logo_contrast", False))
        )
        # Auto-uppdatering 00:00 varje dag (REQ-K4).
        self.auto_update_var = tk.BooleanVar(
            value=bool(self.saved.get("auto_update_daily", True))
        )

        initial_top = self._clamp(self.saved.get("logo_top_px", 5), 0, 100)
        self.logo_top_px_var = tk.IntVar(value=initial_top)

        # ── Instance-attribut ──────────────────────────────
        self.prepared_logo: object = None
        self.logo_kind: str = ""
        self.labels_text: list = []
        self.labels_include: list = []  # checkruta per rad (förslag: checkruta)

        # Återställ senast använda logotyp (om den fortfarande finns).
        self.logo_path: Optional[str] = self.saved.get("last_logo_path") or None
        if self.logo_path and Path(self.logo_path).is_file():
            self.prepared_logo = LabelModule.load_and_resize_logo(self.logo_path)
            if self.prepared_logo:
                suffix = Path(self.logo_path).suffix.lower()
                self.logo_kind = (
                    "vektor" if suffix in LogoModule.VECTOR_FORMATS else "bild"
                )
            else:
                self.logo_path = None
        else:
            self.logo_path = None

        self.setup_gui()
        self.root.bind("<Control-n>", self.add_label_hotkey)
        self.root.bind("<Command-n>", self.add_label_hotkey)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # §8: loggning av appstart + daglig städning (arkivera gårdagens
        # loggar, radera arkiv äldre än 7 dagar).
        housekeeping = LoggModule.logg.daily_housekeeping()
        LoggModule.logg.log_app(
            f"App startad (städning: {housekeeping['arkiverade']} arkiverade, "
            f"{len(housekeeping['raderade'])} arkiv raderade)"
        )

        # REQ-K4: tyst uppdateringskontroll i bakgrunden (ingen nedladdning
        # utan användaren klickar 'Sök uppdatering').
        self._upd_thread: Optional[threading.Thread] = None
        threading.Thread(
            target=self._auto_check_updates, daemon=True
        ).start()

        # Auto-uppdatering 00:00 varje dag (om inställningen är påslagen):
        # schemalägger nästa midnatt; uppcatchar missad midnatt inom 5 min.
        self._auto_upd_queue: "queue.Queue[dict]" = queue.Queue()
        if self.auto_update_var.get():
            self._schedule_auto_update()

    @staticmethod
    def _clamp(value, minimum: int, maximum: int) -> int:
        try:
            return min(maximum, max(minimum, int(value)))
        except (TypeError, ValueError):
            return minimum

    # ──────────────────────────────────────────────────────
    # INSTÄLLNINGAR
    # ──────────────────────────────────────────────────────

    def current_settings(self) -> dict:
        """Samlar ihop alla värden som ska sparas i settings.json."""
        settings = dict(self.saved)
        settings.update({
            "label_type": self.type_var.get(),
            "text_size": self.text_size_var.get(),
            "auto_shrink": bool(self.auto_shrink.get()),
            "multi_label": bool(self.multi_label.get()),
            "cut_lines": bool(self.cut_lines_var.get()),
            "logo_top_px": self.logo_top_px_var.get(),
            "verifikat_year": self.verifikat_year_var.get(),
            "verifikat_per_month": self.verifikat_per_month_var.get(),
            "verifikat_period": self.verifikat_period_var.get(),
            "verifikat_language": self.verifikat_language_var.get(),
            "barcode_labels": bool(self.barcode_var.get()),
            "corner_marks": bool(self.corner_marks_var.get()),
            "logo_contrast": bool(self.logo_contrast_var.get()),
            "auto_update_daily": bool(self.auto_update_var.get()),
            "label_count": self.antal_var.get(),
            "last_logo_path": self.logo_path or "",
            "window_geometry": self.root.geometry(),
        })
        return settings

    def save_settings(self) -> None:
        SettingsModule.save_settings(
            self.current_settings(), SettingsModule.SETTINGS_PATH
        )

    def on_close(self) -> None:
        """Sparar inställningar innan fönstret stängs."""
        self.on_logo_top_changed(save=False)
        self.save_settings()
        self.root.destroy()

    def on_logo_top_changed(self, save: bool = True) -> None:
        """Uppdaterar logotypens avstånd från toppen i LabelModule."""
        value = self._clamp(self.logo_top_px_var.get(), 0, 100)
        try:
            settings = LabelModule.get_current_settings()
            settings.logo_min_top_margin = float(value)
            settings.logo_top_margin = float(value)
            LabelModule.set_current_settings(settings)
            LoggModule.logg.resolve_error("LOGO_MARGIN")
        except Exception as exc:
            LoggModule.logg.log_error(
                "LOGO_MARGIN", f"Kunde inte uppdatera logotypmarginal: {exc}"
            )
            print(f"[Inställning] Kunde inte uppdatera logotypmarginal: {exc}")
        if save:
            self.save_settings()

    # ──────────────────────────────────────────────────────
    # GUI-UPPBYGGNAD
    # ──────────────────────────────────────────────────────

    def setup_gui(self) -> None:
        """Bygger gränssnittet: flikar, vänsterpanel och etikettlista."""
        self.notebook = ttk.Notebook(self.root)
        self.main_tab = ttk.Frame(self.notebook)
        self.help_tab = ttk.Frame(self.notebook)
        self.logg_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.main_tab, text="Generator")
        self.notebook.add(self.help_tab, text="Hjälp")
        self.notebook.add(self.logg_tab, text="Loggar")
        self.notebook.pack(fill="both", expand=True)

        # ── Scrollbar vänsterpanel (alla kontroller nås även på små skärmar) ──
        left_outer = ttk.Frame(self.main_tab, width=330)
        left_outer.pack(side="left", fill="y")
        left_canvas = tk.Canvas(left_outer, highlightthickness=0, width=325)
        left_scrollbar = ttk.Scrollbar(
            left_outer, orient="vertical", command=left_canvas.yview
        )
        left = ttk.Frame(left_canvas, padding=10)
        left.bind(
            "<Configure>",
            lambda event: left_canvas.configure(scrollregion=left_canvas.bbox("all")),
        )
        left_canvas.create_window((0, 0), window=left, anchor="nw")
        left_canvas.configure(yscrollcommand=left_scrollbar.set)
        left_canvas.pack(side="left", fill="both", expand=True)
        left_scrollbar.pack(side="right", fill="y")
        _bind_mousewheel(left_canvas)

        right = ttk.Frame(self.main_tab, padding=10)
        right.pack(side="right", expand=True, fill="both")

        # ══════════════════════════════════════════════════
        # VÄNSTER PANEL
        # ══════════════════════════════════════════════════

        ttk.Label(left, text="Etikettyp", font=("", 10, "bold")).pack(
            anchor="w", pady=(0, 5))
        for text, value in (
            ("Smal (41×64 mm)", "rygg_smal"),
            ("Tjock (57×64 mm)", "rygg_tjock"),
            ("Index (A4)", "index"),
        ):
            ttk.Radiobutton(
                left, text=text, variable=self.type_var, value=value,
                command=lambda: self.update_label_fields(True),
            ).pack(anchor="w")

        ttk.Separator(left, orient="horizontal").pack(fill="x", pady=10)

        # ── Logotyp ───────────────────────────────────────
        ttk.Label(left, text="Logotyp", font=("", 10, "bold")).pack(anchor="w")
        ttk.Label(
            left, text="PDF, SVG, EPS, AI, PNG, JPG …", foreground="gray"
        ).pack(anchor="w", pady=(0, 5))
        ttk.Button(
            left, text="📁 Välj logotyp (PDF/SVG/EPS…)",
            command=self.choose_logo,
        ).pack(fill="x", pady=2)
        ttk.Button(
            left, text="⭐ Använd appens logotyp (vektor)",
            command=self.use_app_logo,
        ).pack(fill="x", pady=2)
        ttk.Button(
            left, text="📂 Öppna Logotyp-mappen",
            command=self.open_logo_folder,
        ).pack(fill="x", pady=2)

        self.logo_label = ttk.Label(
            left, text="Ingen logotyp vald", wraplength=270, foreground="gray"
        )
        self.logo_label.pack(anchor="w", pady=(5, 0))
        self.clear_logo_button = ttk.Button(
            left, text="✕ Ta bort logotyp", command=self.clear_logo
        )
        self.clear_logo_button.pack(fill="x", pady=(4, 0))

        logo_top_frame = ttk.Frame(left)
        logo_top_frame.pack(fill="x", pady=(8, 0))
        ttk.Label(logo_top_frame, text="Logga från topp (px):").pack(side="left")
        ttk.Spinbox(
            logo_top_frame, from_=0, to=100, width=5,
            textvariable=self.logo_top_px_var,
            command=self.on_logo_top_changed,
        ).pack(side="left", padx=(5, 0))
        self.logo_top_px_var.trace_add(
            "write", lambda *_: self.on_logo_top_changed()
        )
        self._refresh_logo_label()

        ttk.Separator(left, orient="horizontal").pack(fill="x", pady=10)

        # ── Inställningar ─────────────────────────────────
        ttk.Label(left, text="Inställningar", font=("", 10, "bold")).pack(
            anchor="w", pady=(0, 5))

        ttk.Label(left, text="Textstorlek:").pack(anchor="w")
        size_frame = ttk.Frame(left)
        size_frame.pack(fill="x")
        ttk.Scale(
            size_frame, from_=8, to=32, variable=self.text_size_var,
            orient="horizontal",
        ).pack(side="left", fill="x", expand=True)
        ttk.Label(size_frame, textvariable=self.text_size_var, width=3).pack(
            side="right")

        ttk.Checkbutton(
            left, text="Autoanpassa text", variable=self.auto_shrink
        ).pack(anchor="w", pady=2)
        ttk.Checkbutton(
            left, text="Flera etiketter", variable=self.multi_label
        ).pack(anchor="w", pady=2)
        ttk.Checkbutton(
            left, text="Klipplinjer (kant till kant)", variable=self.cut_lines_var
        ).pack(anchor="w", pady=2)
        ttk.Checkbutton(
            left, text="Förstärkta hörnmarkeringar (#22)",
            variable=self.corner_marks_var
        ).pack(anchor="w", pady=2)
        ttk.Checkbutton(
            left, text="Streckkod (Code 128) på etiketten (#2)",
            variable=self.barcode_var
        ).pack(anchor="w", pady=2)
        ttk.Checkbutton(
            left, text="Automatisk logotypkontrast (#16)",
            variable=self.logo_contrast_var
        ).pack(anchor="w", pady=2)

        ttk.Label(left, text="Antal etiketter:").pack(anchor="w", pady=(10, 0))
        self.antal_entry = ttk.Spinbox(
            left, from_=1, to=50, textvariable=self.antal_var, width=5,
            command=lambda: self.update_label_fields(True),
        )
        self.antal_entry.pack(anchor="w", pady=(0, 10))

        ttk.Button(
            left, text="📄 SKAPA PDF", command=self.create_pdf,
            style="Accent.TButton",
        ).pack(fill="x", pady=5)
        ttk.Button(
            left, text="🗂 Skapa arkivindex (A4, platskoder) (#1)",
            command=self.create_arkivindex_pdf,
        ).pack(fill="x", pady=2)
        ttk.Button(
            left, text="📤 Öppna Export-mappen", command=self.open_export_folder,
        ).pack(fill="x", pady=2)
        ttk.Button(
            left, text="⬇️ Sök uppdatering (REQ-K4)",
            command=self.check_updates_clicked,
        ).pack(fill="x", pady=2)
        ttk.Checkbutton(
            left, text="🕒 Auto-uppdatering 00:00 varje dag",
            variable=self.auto_update_var,
            command=self._on_auto_update_toggled,
        ).pack(anchor="w", pady=(0, 2))

        ttk.Separator(left, orient="horizontal").pack(fill="x", pady=10)

        # ── Verifikat ─────────────────────────────────────
        ttk.Label(left, text="Verifikat (hela året)", font=("", 10, "bold")).pack(
            anchor="w", pady=(0, 5))

        # Förslag #10: periodläge; förslag #11: språk.
        # OBS: ttk.Combobox stödjer inte 'command=' (tk-option) —
        # händelsen binds via <<ComboboxSelected>> (P0-buggfix v1.4.1).
        period_frame = ttk.Frame(left)
        period_frame.pack(fill="x", pady=2)
        ttk.Label(period_frame, text="Period:").pack(side="left")
        period_combo = ttk.Combobox(
            period_frame, textvariable=self.verifikat_period_var, width=10,
            values=("manad", "kvartal", "halvar"), state="readonly",
        )
        period_combo.pack(side="left", padx=(5, 10))
        period_combo.bind("<<ComboboxSelected>>", self._update_verifikat_info)
        ttk.Label(period_frame, text="Språk:").pack(side="left")
        language_combo = ttk.Combobox(
            period_frame, textvariable=self.verifikat_language_var, width=6,
            values=("se", "en", "no"), state="readonly",
        )
        language_combo.pack(side="left", padx=(5, 0))
        language_combo.bind("<<ComboboxSelected>>", self._update_verifikat_info)

        year_frame = ttk.Frame(left)
        year_frame.pack(fill="x", pady=2)
        ttk.Label(year_frame, text="År:").pack(side="left")
        ttk.Spinbox(
            year_frame, from_=VerifikatModule.MIN_YEAR, to=VerifikatModule.MAX_YEAR,
            textvariable=self.verifikat_year_var, width=7,
        ).pack(side="left", padx=(5, 10))
        ttk.Label(year_frame, text="Lappar/mån:").pack(side="left")
        ttk.Spinbox(
            year_frame,
            from_=VerifikatModule.MIN_PER_MONTH,
            to=VerifikatModule.MAX_PER_MONTH,
            textvariable=self.verifikat_per_month_var, width=4,
            command=self._update_verifikat_info,
        ).pack(side="left", padx=(5, 0))

        self.verifikat_info = ttk.Label(left, foreground="gray", wraplength=270)
        self.verifikat_info.pack(anchor="w", pady=(2, 4))
        self._update_verifikat_info()

        ttk.Button(
            left, text="🧾 Skapa valt antal / månad",
            command=self.create_verifikat_pdf,
        ).pack(fill="x", pady=2)
        ttk.Button(
            left, text="🧾 Skapa BÅDA (1 & 2 per månad)",
            command=self.create_verifikat_both,
            style="Accent.TButton",
        ).pack(fill="x", pady=4)

        # ══════════════════════════════════════════════════
        # HÖGER PANEL — ETIKETTTEXT
        # ══════════════════════════════════════════════════
        ttk.Label(right, text="Etiketttext", font=("", 10, "bold")).pack(anchor="w")

        scroll_frame = ttk.Frame(right)
        scroll_frame.pack(fill="both", expand=True)

        label_canvas = tk.Canvas(scroll_frame)
        scrollbar = ttk.Scrollbar(
            scroll_frame, orient="vertical", command=label_canvas.yview
        )
        self.label_container = ttk.Frame(label_canvas)
        self.label_container.bind(
            "<Configure>",
            lambda event: label_canvas.configure(
                scrollregion=label_canvas.bbox("all")
            ),
        )
        label_canvas.create_window((0, 0), window=self.label_container, anchor="nw")
        label_canvas.configure(yscrollcommand=scrollbar.set)
        label_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        _bind_mousewheel(label_canvas)

        self.update_label_fields()

        # ══════════════════════════════════════════════════
        # HJÄLP-FLIK
        # ══════════════════════════════════════════════════
        tools = LogoModule.check_tools()
        tool_text = (
            f"PyMuPDF (PDF): {'✓' if tools['pymupdf'] else '✗'}, "
            f"Ghostscript: {'✓' if tools['ghostscript'] else '✗'}, "
            f"Inkscape: {'✓' if tools['inkscape'] else '✗'}, "
            f"cairosvg: {'✓' if tools['cairosvg'] else '✗'}"
        )

        help_txt = tk.Text(self.help_tab, wrap="word", font=("", 10))
        help_txt.insert("1.0", f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Pärmetikett Generator — {get_copyright_notice()}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LOGOTYPER:
  • PDF (första sidan), SVG, EPS, AI och raster
    (PNG, JPG, BMP, GIF, TIFF, WEBP)
  • Vektorlogotyper renderas till högupplöst PNG och
    centreras automatiskt på etiketten
  • PDF: PyMuPDF → Ghostscript → Inkscape → pdftoppm
  • SVG:  Inkscape → cairosvg → PyMuPDF
  • EPS:  Ghostscript → Inkscape
  • Konverteringsverktyg: {tool_text}

ETIKETTYPER:
  • Rygg Smal:  41 × 64 mm
  • Rygg Tjock: 57 × 64 mm
  • Index:      12 rader på A4 med numrering

VERIFIKAT — HELA ÅRET:
  • "Skapa BÅDA (1 & 2 per månad)" gör två PDF:er:
      verifikat_<år>_1_per_manad.pdf  (12 lappar)
      verifikat_<år>_2_per_manad.pdf  (24 lappar)
  • Ordningen är alltid JAN 1, JAN 2, FEB 1, …
  • "Skapa valt antal / månad" klarar även 3–12 lappar/månad
  • Period: månader, kvartal (Q1–Q4) eller halvår (H1–H2)  [#10]
  • Språk: se / en / no styr månadsförkortningarna          [#11]
  • Använder vald etikettyp, logotyp, marginaler och klipplinjer

NYA FUNKTIONER (v1.1.0):
  • Checkruta per etikettrad — kryssa för vad som ska skrivas ut
  • Streckkod (Code 128-B) i etikettens underkant             [#2]
  • Förstärkta hörnmarkeringar för exakt trimning             [#22]
  • Automatisk logotypkontrast: mörka logotyper får vit baksida [#16]
  • Arkivindex (A4) med platskoder A1-01, A1-02 … av alla
    ikryssade etiketter                                       [#1]

ANPASSNING:
  • Texten krymper automatiskt tills den får plats
  • Logotypens storlek och toppavstånd justeras i vänsterpanelen
  • Klipplinjer kan slås av/på
  • Inställningar sparas i settings.json

EXPORT:
  • Alla PDF:er sparas i {LabelModule.get_export_folder()}

KORTKOMMANDON:
  • Ctrl+N: nytt etikettfält
  • Mushjul: scroll i båda panelerna

LOGGAR (§8):
  • Fellogg visar alla AKTIVA fel — åtgärdade fel försvinner
    automatiskt, och kan även rensas manuellt på Loggar-fliken
  • Applogg sparar händelser (PDF:er, logotyper, städning)
  • Gårdagens loggposter arkiveras; arkivet rensas efter 7 dagar

SKÄRM & SKÄRPA (§11):
  • Fönstret startar i max höjd-läge (anpassat efter skärmen) med
    anpassad bredd — inget terminalfönster behövs (kör pythonw.exe)
  • DPI-medveten rendering (Windows) → skarp text på 4K/skalning
  • Loggar-flikens kolumner kan sorteras (klick) och flyttas (dra)

UPDATER (REQ-K4, §3):
  • 'Sök uppdatering' jämför filer (namn + sha256) mot senaste
    Latest-release och uppdaterar ENDAST det som skiljer
  • Backup skapas först; den tas bort FÖRST när uppdateringen
    verifierats som lyckad — annars full rollback
  • Releaser som pekar på 'main' uppdateras aldrig (§1)
  • Tyst kontroll vid start (loggas i apploggen) — nedladdning sker
    först när du klickar 'Sök uppdatering'
  • AUTO-UPDATERING 00:00: varje midnatt körs uppdateringen automatiskt
    (om en nyare release finns) — helt tyst, loggas i apploggen; missad
    midnatt uppcatchas om appen startar inom 5 minuter efter 00:00.
    Av/på-knapp i vänsterpanelen.

UPDATER (REQ-K4, §3):
  • 'Sök uppdatering' jämför filer (namn + sha256) mot senaste
    Latest-release och uppdaterar ENDAST det som skiljer
  • Backup skapas först; den tas bort FÖRST när uppdateringen
    verifierats som lyckad — annars full rollback
  • Releaser som pekar på 'main' vägras aldrig uppdateras (§1)
  • Tyst kontroll vid start (loggas i apploggen) — nedladdning sker
    först när du klickar 'Sök uppdatering'

LOGGOTYPMAPP:
  {DEFAULT_LOGO_FOLDER}
        """)
        help_txt.config(state="disabled")
        help_txt.pack(fill="both", expand=True, padx=10, pady=10)

        # ══════════════════════════════════════════════════
        # LOGGAR-FLIK — §8: fellogg (aktiva fel) + applogg
        # ══════════════════════════════════════════════════
        fel_frame = ttk.LabelFrame(self.logg_tab, text="Fellogg — aktiva fel "
                                   "(åtgärdade fel försvinner automatiskt)",
                                   padding=8)
        fel_frame.pack(fill="both", expand=True, padx=10, pady=(10, 5))

        fel_columns = ("tid", "kod", "meddelande", "antal")
        self.fel_tree = ttk.Treeview(
            fel_frame, columns=fel_columns, show="headings", height=8
        )
        for column, text, width in (
            ("tid", "Tid", 150),
            ("kod", "Kod", 130),
            ("meddelande", "Meddelande", 460),
            ("antal", "Antal", 60),
        ):
            self.fel_tree.heading(column, text=text)
            self.fel_tree.column(column, width=width, anchor="w")
        GuiHelpersModule.make_treeview_interactive(self.fel_tree, fel_columns)
        fel_scroll = ttk.Scrollbar(
            fel_frame, orient="vertical", command=self.fel_tree.yview
        )
        self.fel_tree.configure(yscrollcommand=fel_scroll.set)
        self.fel_tree.pack(side="left", fill="both", expand=True)
        fel_scroll.pack(side="right", fill="y")

        fel_buttons = ttk.Frame(self.logg_tab)
        fel_buttons.pack(fill="x", padx=10)
        ttk.Button(
            fel_buttons, text="✕ Rensa valda fel",
            command=self._clear_selected_errors,
        ).pack(side="left", padx=(0, 5))
        ttk.Button(
            fel_buttons, text="🗑 Rensa alla",
            command=self._clear_all_errors,
        ).pack(side="left")
        ttk.Button(
            fel_buttons, text="🔄 Uppdatera", command=self._refresh_loggar
        ).pack(side="right")

        app_frame = ttk.LabelFrame(self.logg_tab, text="Applogg (senaste 100)",
                                   padding=8)
        app_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        self.applog_text = tk.Text(
            app_frame, height=10, wrap="none", state="disabled",
            font=("Consolas", 9) if sys.platform.startswith("win") else ("", 9),
        )
        applog_scroll = ttk.Scrollbar(
            app_frame, orient="vertical", command=self.applog_text.yview
        )
        self.applog_text.configure(yscrollcommand=applog_scroll.set)
        self.applog_text.pack(side="left", fill="both", expand=True)
        applog_scroll.pack(side="right", fill="y")

        self._refresh_loggar()
        self.notebook.bind(
            "<<NotebookTabChanged>>", self._on_tab_changed
        )

    def _update_verifikat_info(self, *_args) -> None:
        """Visar hur många lappar den valda varianten ger."""
        try:
            period = VerifikatModule.validate_period_mode(
                self.verifikat_period_var.get()
            )
            language = VerifikatModule.validate_language(
                self.verifikat_language_var.get()
            )
            count = VerifikatModule.validate_per_month(
                self.verifikat_per_month_var.get()
            )
            periods = VerifikatModule.period_labels(period, language)
            word = VerifikatModule.PERIOD_MODES[period]["sv"]
            self.verifikat_info.config(
                text=f"→ {len(periods) * count} lappar "
                     f"({len(periods)} {word} × {count})"
            )
        except (tk.TclError, ValueError):
            self.verifikat_info.config(text="→ Ange 1–12 lappar per månad")

    # ──────────────────────────────────────────────────────
    # ETIKETTFÄLT
    # ──────────────────────────────────────────────────────

    def update_label_fields(self, preserve_content: bool = False) -> None:
        """Skapar/uppdaterar textfälten i höger panel (med checkruta per rad)."""
        previous = (
            [text.get("1.0", tk.END).strip() for text in self.labels_text]
            if preserve_content else []
        )
        previous_include = (
            [bool(var.get()) for var in self.labels_include]
            if preserve_content else []
        )
        for widget in self.label_container.winfo_children():
            widget.destroy()
        self.labels_text.clear()
        self.labels_include.clear()

        count = 12 if self.type_var.get() == "index" else self.antal_var.get()
        for index in range(count):
            frame = ttk.Frame(self.label_container)
            frame.pack(fill="x", pady=2, padx=5)
            include_var = tk.BooleanVar(
                value=previous_include[index] if index < len(previous_include)
                else True
            )
            ttk.Checkbutton(
                frame, variable=include_var,
            ).pack(side="left")
            ttk.Label(frame, text=f"Etikett {index + 1}:", width=10).pack(side="left")
            text_widget = tk.Text(frame, height=2, width=40)
            text_widget.pack(side="left", fill="x", expand=True, padx=(5, 0))
            if index < len(previous):
                text_widget.insert("1.0", previous[index])
            self.labels_text.append(text_widget)
            self.labels_include.append(include_var)

    def _included_texts(self) -> List[str]:
        """Texterna från rader med ikryssad checkruta (i ordning)."""
        texts = []
        for text_widget, include_var in zip(self.labels_text, self.labels_include):
            if include_var.get():
                texts.append(text_widget.get("1.0", tk.END).strip())
        return texts

    def _barcode_text_for(self, label_text: str) -> Optional[str]:
        """Streckkodsinnehåll för en etikett: första användbara raden.

        Tar textens första rad (verifikat: period + nummer + år), begränsar
        till ASCII 32–126 och max 24 tecken för bra scanningsbarhet.
        """
        rows = [row.strip() for row in (label_text or "").split("\n") if row.strip()]
        if not rows:
            return None
        candidate = rows[0] if rows[0].upper() != "VERIFIKAT" else (
            " ".join(rows[1:4]) if len(rows) >= 4 else rows[-1]
        )
        cleaned = "".join(
            char for char in candidate if 32 <= ord(char) <= 126
        ).strip()
        if not cleaned:
            return None
        return cleaned[:24]

    def add_label_hotkey(self, event=None) -> None:
        """Ctrl+N lägger till ett etikettfält (max 50)."""
        if self.type_var.get() == "index":
            messagebox.showinfo("Info", "Index har alltid exakt 12 fält.")
            return
        if self.antal_var.get() < 50:
            self.antal_var.set(self.antal_var.get() + 1)
            self.update_label_fields(preserve_content=True)

    # ──────────────────────────────────────────────────────
    # LOGGAR-FLIK (§8)
    # ──────────────────────────────────────────────────────

    def _on_tab_changed(self, _event=None) -> None:
        """Uppdaterar loggflikarna när fliken visas."""
        try:
            current = self.notebook.index(self.notebook.select())
            if self.notebook.nametowidget(
                self.notebook.tabs()[current]
            ) is self.logg_tab:
                self._refresh_loggar()
        except Exception:
            pass

    def _refresh_loggar(self) -> None:
        """Fyller felloggen (aktiva fel) och apploggvyerna."""
        self.fel_tree.delete(*self.fel_tree.get_children())
        for entry in LoggModule.logg.active_errors():
            self.fel_tree.insert("", "end", iid=str(entry.get("kod")), values=(
                entry.get("ts", ""),
                entry.get("kod", ""),
                entry.get("meddelande", ""),
                entry.get("antal", 1),
            ))
        self.applog_text.config(state="normal")
        self.applog_text.delete("1.0", tk.END)
        for entry in LoggModule.logg.recent_app(100):
            self.applog_text.insert(
                tk.END,
                f"{entry.get('ts', '')}  [{entry.get('nivå', 'INFO')}]  "
                f"{entry.get('meddelande', '')}\n",
            )
        self.applog_text.see(tk.END)
        self.applog_text.config(state="disabled")

    def _clear_selected_errors(self) -> None:
        """Rensar användarens valda fel (de är åtgärdade)."""
        selection = self.fel_tree.selection()
        if not selection:
            messagebox.showinfo("Rensa fel", "Välj först fel att rensa.")
            return
        removed = LoggModule.logg.clear_errors(list(selection))
        LoggModule.logg.log_app(f"{removed} fel rensade manuellt", "INFO")
        self._refresh_loggar()

    def _clear_all_errors(self) -> None:
        """Rensar alla fel (alla är åtgärdade)."""
        removed = LoggModule.logg.clear_errors(None)
        LoggModule.logg.log_app(f"Alla fel rensade ({removed} st)", "INFO")
        self._refresh_loggar()

    # ──────────────────────────────────────────────────────
    # UPDATER (REQ-K4, §3) — jämför filer mot Latest-release
    # ──────────────────────────────────────────────────────

    def _auto_check_updates(self) -> None:
        """Tyst startkontroll: finns en nyare release? (loggas i applog)"""
        try:
            result = UpdaterModule.check_for_new_release()
            if result.get("ny_release"):
                LoggModule.logg.log_app(
                    f"Ny release {result['tag']} finns "
                    f"(installerad: {result['installed']}) — "
                    "välj 'Sök uppdatering'", "VARNING"
                )
            else:
                LoggModule.logg.log_app(
                    f"Uppdateringskontroll: senaste version redan installerad "
                    f"({result.get('installed')})"
                )
        except Exception as exc:
            LoggModule.logg.log_error(
                "UPD_CHECK", f"Startkontroll misslyckades: {exc}"
            )

    def check_updates_clicked(self) -> None:
        """Kör full uppdatering (jämför filer → backup → verifiera) i bakgrund."""
        if self._upd_thread is not None and self._upd_thread.is_alive():
            messagebox.showinfo(
                "Pågår", "En uppdateringskontroll körs redan — vänta lite."
            )
            return
        LoggModule.logg.log_app(
            "Uppdatering startad manuellt (filjämförelse mot Latest-release)"
        )
        result_queue: "queue.Queue[dict]" = queue.Queue()
        self._upd_thread = threading.Thread(
            target=lambda: result_queue.put(UpdaterModule.run_update()),
            daemon=True,
        )
        self._upd_thread.start()

        def poll() -> None:
            if result_queue.empty():
                self.root.after(150, poll)
                return
            result = result_queue.get_nowait()
            self._show_update_result(result)

        self.root.after(150, poll)

    def _on_auto_update_toggled(self) -> None:
        """(Av)aktiverar 00:00-auto-uppdateringen direkt + sparar."""
        self.save_settings()
        if self.auto_update_var.get():
            LoggModule.logg.log_app("Auto-uppdatering 00:00 påslagen")
            self._schedule_auto_update()
        else:
            LoggModule.logg.log_app("Auto-uppdatering 00:00 avslagen")

    def _schedule_auto_update(self) -> None:
        """Schemalägger nästa 00:00-auto-uppdatering (uppcatchning = nu)."""
        if not self.auto_update_var.get():
            return
        delay_ms = UpdaterModule.next_midnight_delay()
        self.root.after(max(0, delay_ms), self._trigger_auto_update)

    def _trigger_auto_update(self) -> None:
        """Kör tyst auto-uppdatering i bakgrund (00:00 eller uppcatchning)."""
        if not self.auto_update_var.get():
            return
        threading.Thread(
            target=lambda: self._auto_upd_queue.put(
                UpdaterModule.auto_update()
            ),
            daemon=True,
        ).start()
        self.root.after(200, self._poll_auto_update)

    def _poll_auto_update(self) -> None:
        """Hämtar auto-uppdateringsresultat (main-thread) + schemalägger om."""
        if self._auto_upd_queue.empty():
            self.root.after(300, self._poll_auto_update)
            return
        result = self._auto_upd_queue.get_nowait()
        if result.get("uppdaterad"):
            status = f"uppdaterad till {result.get('tag')}"
        elif result.get("ok"):
            status = "ingen uppdatering behövs"
        else:
            status = f"misslyckades ({result.get('fel', 'okänt')})"
        LoggModule.logg.log_app(f"AUTO-UPD klar: {status}")
        self._schedule_auto_update()  # nästa midnatt

    def _show_update_result(self, result: dict) -> None:
        """Visar uppdateringsresultat för användaren."""
        if result.get("ok") and result.get("uppdaterad"):
            messagebox.showinfo(
                "Uppdatering klar ✅",
                f"Uppdaterad till {result.get('tag')}!\n\n"
                f"Uppdaterade filer: {result.get('copied')}\n"
                f"Raderade gamla filer: {result.get('removed')}\n"
                f"Oförändrade: {result.get('unchanged')}\n\n"
                f"Verifiering: OK\n"
                f"Backup: borttagen efter lyckad verifiering\n\n"
                f"Starta om appen för att alla ändringar ska gälla.\n"
                f"{get_copyright_notice()}",
            )
        elif result.get("ok"):
            messagebox.showinfo(
                "Ingen uppdatering behövs",
                result.get("meddelande", "Du har redan senaste versionen."),
            )
        else:
            LoggModule.logg.log_error(
                "UPD_APPLY", result.get("fel", "Okänt uppdateringsfel")
            )
            messagebox.showerror(
                "Uppdatering misslyckades",
                f"{result.get('fel', 'Okänt fel')}\n\n"
                f"Se Loggar-fliken för detaljer.",
            )

    # ──────────────────────────────────────────────────────
    # LOGOTYP
    # ──────────────────────────────────────────────────────

    def _refresh_logo_label(self) -> None:
        """Uppdaterar statusraden för vald logotyp."""
        if self.logo_path and self.prepared_logo:
            name = Path(self.logo_path).name
            size = f"{self.prepared_logo.width}×{self.prepared_logo.height}"
            kind = self.logo_kind or "bild"
            self.logo_label.config(
                text=f"✓ {name}\n({size} px, {kind})", foreground="green"
            )
            self.clear_logo_button.config(state="normal")
        else:
            self.logo_label.config(text="Ingen logotyp vald", foreground="gray")
            self.clear_logo_button.config(state="disabled")

    def choose_logo(self) -> None:
        """Väljer och laddar en logotyp (PDF/SVG/EPS/AI/raster)."""
        filepath, filetype = LogoModule.select_logo_file(self.root)
        if not filepath:
            return
        prepared = LabelModule.load_and_resize_logo(filepath)
        if not prepared:
            LoggModule.logg.log_error(
                "LOGO_LOAD", f"Kunde inte läsa {Path(filepath).name}"
            )
            messagebox.showerror(
                "Logotypen kunde inte läsas",
                f"Kunde inte läsa {Path(filepath).name}.\n\n"
                "Kontrollera filen och att ett konverteringsverktyg "
                "finns installerat (se Hjälp-fliken).",
            )
            return
        self.logo_path = filepath
        self.prepared_logo = prepared
        self.logo_kind = filetype or "bild"
        LoggModule.logg.resolve_error("LOGO_LOAD")   # åtgärdat → bort från felloggen
        LoggModule.logg.log_app(f"Logotyp vald: {Path(filepath).name}")
        self._refresh_logo_label()
        self.save_settings()

    def use_app_logo(self) -> None:
        """Använder appens egen vektorlogotyp som etikettlogotyp."""
        if not APP_LOGOTYP_SVG.is_file():
            messagebox.showerror(
                "Saknas", f"Appens logotyp finns inte: {APP_LOGOTYP_SVG}"
            )
            return
        prepared = LabelModule.load_and_resize_logo(str(APP_LOGOTYP_SVG))
        if not prepared:
            LoggModule.logg.log_error("LOGO_LOAD", "Appens logotyp kunde inte läsas")
            messagebox.showerror(
                "Logotypen kunde inte läsas",
                "Appens logotyp kunde inte läsas — se Loggar-fliken.",
            )
            return
        self.logo_path = str(APP_LOGOTYP_SVG)
        self.prepared_logo = prepared
        self.logo_kind = "vektor"
        LoggModule.logg.resolve_error("LOGO_LOAD")
        LoggModule.logg.log_app("Appens logotyp vald")
        self._refresh_logo_label()
        self.save_settings()

    def clear_logo(self) -> None:
        """Tar bort den valda logotypen."""
        self.logo_path = None
        self.prepared_logo = None
        self.logo_kind = ""
        self._refresh_logo_label()
        self.save_settings()

    def open_logo_folder(self) -> None:
        DEFAULT_LOGO_FOLDER.mkdir(parents=True, exist_ok=True)
        self._open_folder_in_os(DEFAULT_LOGO_FOLDER)

    def open_export_folder(self) -> None:
        self._open_folder_in_os(LabelModule.get_export_folder())

    def _open_folder_in_os(self, folder: Path) -> None:
        """Öppnar en mapp i OS-filhanteraren."""
        try:
            if sys.platform.startswith("win"):
                os.startfile(folder)  # type: ignore[attr-defined]
            elif sys.platform.startswith("darwin"):
                subprocess.run(["open", str(folder)], check=False)
            else:
                subprocess.run(["xdg-open", str(folder)], check=False)
        except Exception as exc:
            LoggModule.logg.log_error("MAPPOPEN", str(exc))
            messagebox.showerror("Fel", f"Kunde inte öppna mappen:\n{exc}")

    # ──────────────────────────────────────────────────────
    # KLIPPLINJER
    # ──────────────────────────────────────────────────────

    def _draw_cut_lines(
        self,
        c: canvas.Canvas,
        width: float,
        height: float,
        cols: int,
        rows: int,
    ) -> None:
        """Ritar streckade klipplinjer kant till kant över hela arket."""
        if not self.cut_lines_var.get():
            return

        c.saveState()
        c.setStrokeColor(CUT_LINE_COLOR)
        c.setLineWidth(CUT_LINE_WIDTH)
        c.setDash(*CUT_LINE_DASH)

        x_positions: set[float] = set()
        for col in range(cols):
            x_left = PDF_SIDE_MARGIN + col * (width + PDF_SPACING)
            x_positions.add(round(x_left, 3))
            x_positions.add(round(x_left + width, 3))
        for x in sorted(x_positions):
            c.line(x, 0, x, A4_HEIGHT)

        y_positions: set[float] = set()
        for row in range(rows):
            y_top = A4_HEIGHT - PDF_TOP_MARGIN - row * (height + PDF_SPACING)
            y_positions.add(round(y_top, 3))
            y_positions.add(round(y_top - height, 3))
        for y in sorted(y_positions):
            c.line(0, y, A4_WIDTH, y)

        c.restoreState()

    # ──────────────────────────────────────────────────────
    # RYGGETIKETTER / INDEX
    # ──────────────────────────────────────────────────────

    def create_pdf(self) -> None:
        """Skapar PDF för rygg-/indexetiketter i export/-mappen.

        Endast rader med ikryssad checkruta inkluderas (checkrutaval).
        """
        self.on_logo_top_changed(save=False)
        label_type = self.type_var.get()
        all_texts = self._included_texts()

        if label_type == "index":
            if len(self.labels_text) != 12:
                messagebox.showerror("Fel", "Index kräver exakt 12 etikettfält.")
                return
            texts = [text for text in all_texts if text] or [
                text.get("1.0", tk.END).strip() for text in self.labels_text
            ]
        else:
            texts = (
                [text for text in all_texts if text]
                if self.multi_label.get()
                else ([all_texts[0]] if all_texts and all_texts[0] else [])
            )
            if not texts:
                messagebox.showerror(
                    "Fel",
                    "Inga giltiga etiketter ifyllda.\n"
                    "Kryssa för de rader som ska skrivas ut.",
                )
                return

        title = re.sub(r'[\\/*?:"<>|]', "", texts[0].split("\n")[0])[:40]
        title = title.replace(" ", "_") or "etikett"
        out_path = _get_out_path(f"{label_type}_{title}.pdf")

        try:
            c = canvas.Canvas(str(out_path), pagesize=A4, pageCompression=1)
            if label_type == "index":
                self.draw_index_labels(c, texts)
            else:
                self.draw_spine_labels(c, texts)
            c.save()
        except Exception as exc:
            LoggModule.logg.log_error("PDF_CREATE", str(exc))
            messagebox.showerror(
                "Fel", f"PDF kunde inte skapas:\n{exc}\n\nSe Loggar-fliken."
            )
            return None

        LoggModule.logg.resolve_error("PDF_CREATE")
        LoggModule.logg.log_app(
            f"PDF skapad: {out_path.name} ({len(texts)} etiketter)"
        )
        self.save_settings()
        messagebox.showinfo(
            "PDF skapad",
            f"✓ {out_path.name}\n\nSparad i:\n{out_path.parent}\n\n"
            f"{get_copyright_notice()}",
        )
        self.open_file(out_path)

    def draw_spine_labels(self, c: canvas.Canvas, texts: List[str]) -> None:
        """Ritar ryggetiketter i rutnät med klipplinjer."""
        if not texts:
            return
        width = BINDER_SMALL_WIDTH if self.type_var.get() == "rygg_smal" \
            else BINDER_THICK_WIDTH
        height = BINDER_HEIGHT
        cols, rows = _grid_size(width, height)
        per_page = cols * rows
        self._draw_cut_lines(c, width, height, cols, rows)

        font_name = LabelModule.get_bold_font()
        corner_marks = bool(self.corner_marks_var.get())
        logo_contrast = bool(self.logo_contrast_var.get())
        use_barcode = bool(self.barcode_var.get())
        for index, text in enumerate(texts):
            if index and index % per_page == 0:
                c.showPage()
                self._draw_cut_lines(c, width, height, cols, rows)

            slot = index % per_page
            col, row = divmod(slot, rows)
            x = PDF_SIDE_MARGIN + col * (width + PDF_SPACING)
            y = (A4_HEIGHT - PDF_TOP_MARGIN
                 - (row + 1) * height - row * PDF_SPACING)

            LabelModule.draw_single_label(
                c, x, y, width, height, text,
                prepared_logo_image=self.prepared_logo,
                base_font_name=font_name,
                initial_font_size=self.text_size_var.get(),
                auto_shrink_text=self.auto_shrink.get(),
                barcode_text=(
                    self._barcode_text_for(text) if use_barcode else None
                ),
                corner_marks=corner_marks,
                logo_contrast=logo_contrast,
            )

    def draw_index_labels(self, c: canvas.Canvas, texts: List[str]) -> None:
        """Ritar 12 indexetiketter på A4."""
        margin_top = PDF_TOP_MARGIN
        spacing = 2 * mm
        height = 18 * mm
        label_width = A4_WIDTH - 2 * PDF_SIDE_MARGIN

        if self.prepared_logo:
            margin_top += LabelModule.draw_logo_on_page(
                c, self.prepared_logo, "index"
            ) + 5 * mm

        if self.cut_lines_var.get():
            c.saveState()
            c.setStrokeColor(CUT_LINE_COLOR)
            c.setLineWidth(CUT_LINE_WIDTH)
            c.setDash(*CUT_LINE_DASH)
            x_left = PDF_SIDE_MARGIN
            x_right = PDF_SIDE_MARGIN + label_width
            c.line(x_left, 0, x_left, A4_HEIGHT)
            c.line(x_right, 0, x_right, A4_HEIGHT)
            for index in range(len(texts)):
                y_top = A4_HEIGHT - margin_top - index * (height + spacing)
                c.line(0, y_top, A4_WIDTH, y_top)
                c.line(0, y_top - height, A4_WIDTH, y_top - height)
            c.restoreState()

        font_name = LabelModule.get_bold_font()
        for index, text in enumerate(texts):
            y = A4_HEIGHT - margin_top - index * (height + spacing)
            display_text = (
                f"{index + 1}. {text.strip()}" if text.strip() else f"{index + 1}."
            )
            LabelModule.draw_single_label(
                c, PDF_SIDE_MARGIN, y - height, label_width, height,
                display_text,
                prepared_logo_image=None,
                base_font_name=font_name,
                initial_font_size=12,
                auto_shrink_text=True,
                corner_marks=bool(self.corner_marks_var.get()),
            )

    # ──────────────────────────────────────────────────────
    # VERIFIKAT — HELA ÅRET, 1 OCH 2 PER MÅNAD
    # ──────────────────────────────────────────────────────

    def build_verifikat_texts(self, year: int, per_month: int) -> List[str]:
        """Bygger etiketttexter för hela året (valt periodläge och språk)."""
        return VerifikatModule.build_verifikat_texts(
            year, per_month,
            language=self.verifikat_language_var.get(),
            period=self.verifikat_period_var.get(),
        )

    def create_verifikat_pdf(
        self, per_month: Optional[int] = None, show_message: bool = True
    ) -> Optional[Path]:
        """Skapar en verifikat-PDF för hela året.

        Args:
            per_month: 1, 2 … 12. None använder värdet i GUI:t.
            show_message: Visa bekräftelse och öppna filen (False vid
                massgenerering av flera varianter).

        Returns:
            Sökvägen till PDF:en, eller None vid fel/avbrutett val.
        """
        self.on_logo_top_changed(save=False)
        try:
            year = VerifikatModule.validate_year(self.verifikat_year_var.get())
            count = VerifikatModule.validate_per_month(
                self.verifikat_per_month_var.get() if per_month is None else per_month
            )
            period = VerifikatModule.validate_period_mode(
                self.verifikat_period_var.get()
            )
            language = VerifikatModule.validate_language(
                self.verifikat_language_var.get()
            )
        except (tk.TclError, ValueError) as exc:
            if show_message:
                messagebox.showerror("Fel", str(exc))
            return None

        label_type = self.type_var.get()
        if label_type == "index":
            label_type = "rygg_smal"
        width = BINDER_SMALL_WIDTH if label_type == "rygg_smal" \
            else BINDER_THICK_WIDTH
        height = BINDER_HEIGHT
        texts = self.build_verifikat_texts(year, count)

        out_path = _get_out_path(
            VerifikatModule.verifikat_filename(year, count, period=period)
        )
        try:
            c = canvas.Canvas(str(out_path), pagesize=A4, pageCompression=1)
            self._draw_verifikat_labels(c, texts, width, height)
            c.save()
        except Exception as exc:
            LoggModule.logg.log_error("VERIFIKAT_CREATE", str(exc))
            if show_message:
                messagebox.showerror(
                    "Fel", f"Verifikat kunde inte skapas:\n{exc}\n\nSe Loggar-fliken."
                )
            return None

        LoggModule.logg.resolve_error("VERIFIKAT_CREATE")
        LoggModule.logg.log_app(f"Verifikat skapad: {out_path.name} ({len(texts)} lappar)")
        self.save_settings()

        if show_message:
            word = VerifikatModule.PERIOD_MODES[period]["sv"]
            messagebox.showinfo(
                "Verifikat skapade",
                f"✓ {out_path.name}\n\n"
                f"År: {year}\n"
                f"Lappar per period ({word}): {count}\n"
                f"Språk: {language.upper()}\n"
                f"Totalt antal lappar: {len(texts)}\n\n"
                f"Sparad i:\n{out_path.parent}\n\n"
                f"Etikettyp: {'Smal' if width == BINDER_SMALL_WIDTH else 'Tjock'}\n"
                f"{get_copyright_notice()}",
            )
            self.open_file(out_path)
        return out_path

    def create_verifikat_both(self) -> None:
        """Skapar både 1/månad och 2/månad för hela året i ett svep."""
        self.on_logo_top_changed(save=False)
        try:
            year = VerifikatModule.validate_year(self.verifikat_year_var.get())
        except (tk.TclError, ValueError) as exc:
            messagebox.showerror("Fel", str(exc))
            return

        created = []
        for count in (1, 2):
            path = self.create_verifikat_pdf(count, show_message=False)
            if path:
                created.append((count, path))

        if not created:
            return
        try:
            period = VerifikatModule.validate_period_mode(
                self.verifikat_period_var.get()
            )
            language = VerifikatModule.validate_language(
                self.verifikat_language_var.get()
            )
        except (tk.TclError, ValueError):
            period, language = VerifikatModule.DEFAULT_PERIOD, \
                VerifikatModule.DEFAULT_LANGUAGE
        periods = VerifikatModule.period_labels(period, language)
        word = VerifikatModule.PERIOD_MODES[period]["sv"]
        details = "\n".join(
            f"• {path.name} — {len(periods) * count} lappar ({count}/{word})"
            for count, path in created
        )
        messagebox.showinfo(
            "Verifikat för hela året skapade",
            f"✓ {len(created)} PDF:er för {year}\n\n{details}\n\n"
            f"Sparade i:\n{created[0][1].parent}\n\n"
            f"Varje PDF innehåller alla perioder i ordning.\n"
            f"{get_copyright_notice()}",
        )
        self._open_folder_in_os(created[0][1].parent)

    def _draw_verifikat_labels(
        self,
        c: canvas.Canvas,
        texts: List[str],
        width: float,
        height: float,
    ) -> None:
        """Ritar verifikatetiketter i rutnät, med sidbrytning."""
        font_name = LabelModule.get_bold_font()
        corner_marks = bool(self.corner_marks_var.get())
        logo_contrast = bool(self.logo_contrast_var.get())
        use_barcode = bool(self.barcode_var.get())

        def draw_label(pdf, x, y, label_width, label_height, text) -> None:
            LabelModule.draw_single_label(
                pdf, x, y, label_width, label_height, text,
                prepared_logo_image=self.prepared_logo,
                base_font_name=font_name,
                initial_font_size=self.text_size_var.get(),
                auto_shrink_text=self.auto_shrink.get(),
                barcode_text=(
                    self._barcode_text_for(text) if use_barcode else None
                ),
                corner_marks=corner_marks,
                logo_contrast=logo_contrast,
            )

        def cut_lines(cols, rows) -> None:
            self._draw_cut_lines(c, width, height, cols, rows)

        VerifikatModule.draw_verifikat_labels(
            c, texts, width, height, draw_label, cut_lines,
            page_size=A4,
            side_margin=PDF_SIDE_MARGIN,
            top_margin=PDF_TOP_MARGIN,
            spacing=PDF_SPACING,
        )

    # ──────────────────────────────────────────────────────
    # ARKIVINDEX — förslag #1: A4-indexark med platskoder
    # ──────────────────────────────────────────────────────

    def create_arkivindex_pdf(self) -> Optional[Path]:
        """Skapar ett A4-arkivindex av de ikryssade etiketterna."""
        texts = [text for text in self._included_texts() if text]
        if not texts:
            messagebox.showerror(
                "Fel",
                "Inga etiketter valda.\nKryssa för de rader som ska "
                "ingå i arkivindexet.",
            )
            return None

        entries = ArkivindexModule.build_index_entries(texts)
        out_path = _get_out_path(ArkivindexModule.arkivindex_filename())
        try:
            ArkivindexModule.draw_arkivindex_pdf(
                out_path, entries,
                subtitle=f"Pärmetikett Generator {get_copyright_year()}",
            )
        except Exception as exc:
            LoggModule.logg.log_error("ARKIVINDEX_CREATE", str(exc))
            messagebox.showerror(
                "Fel", f"Arkivindex kunde inte skapas:\n{exc}\n\nSe Loggar-fliken."
            )
            return None

        LoggModule.logg.resolve_error("ARKIVINDEX_CREATE")
        LoggModule.logg.log_app(
            f"Arkivindex skapat: {out_path.name} ({len(entries)} pärmar)"
        )
        self.save_settings()
        messagebox.showinfo(
            "Arkivindex skapat",
            f"✓ {out_path.name}\n\n{len(entries)} pärmar med platskoder "
            f"({entries[0].platskod}–{entries[-1].platskod})\n\n"
            f"Sparad i:\n{out_path.parent}\n\n{get_copyright_notice()}",
        )
        self.open_file(out_path)
        return out_path

    # ──────────────────────────────────────────────────────
    # ÖPPNA GENERERAD FIL
    # ──────────────────────────────────────────────────────

    def open_file(self, path: Path) -> None:
        """Öppnar en genererad PDF i OS-standardprogrammet."""
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform.startswith("darwin"):
                subprocess.run(["open", str(path)], check=False)
            else:
                subprocess.run(["xdg-open", str(path)], check=False)
        except Exception as exc:
            LoggModule.logg.log_error("OPPNA_PDF", str(exc))
            messagebox.showerror("Öppningsfel", str(exc))


# ──────────────────────────────────────────────────────────
# STARTFUNKTION
# ──────────────────────────────────────────────────────────

def main() -> None:
    """Startar Pärmetikett Generator (DPI-medveten, skarp, utan terminal)."""
    LabelModule.register_preferred_bold_font()
    # §11: DPI-medvetenhet FÖRE fönstret skapas → skarp text på hög-DPI.
    dpi_enabled = SkarmModule.enable_dpi_awareness()

    saved = SettingsModule.load_settings()
    root = _create_root()
    # §11: skalning + tydliga typsnitt efter skärmens DPI.
    SkarmModule.apply_scaling(root)
    SkarmModule.configure_fonts(root)

    # Logotyp/ikon: appens vektorlogotyp som fönsterikon (överallt).
    try:
        if APP_LOGOTYP_ICON.is_file():
            icon = tk.PhotoImage(file=str(APP_LOGOTYP_ICON))
            root.iconphoto(True, icon)
            root._app_icon_ref = icon  # hindra skräpsamling
    except Exception as exc:
        print(f"[Ikon] Kunde inte sätta fönsterikon: {exc}")

    if not dpi_enabled:
        print("[DPI] Windows-DPI-medvetenhet kunde inte aktiveras (no-op).")

    LabelGUI(root, saved)
    root.mainloop()


if __name__ == "__main__":
    main()
