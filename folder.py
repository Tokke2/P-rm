# Fil: folder.py — GUI för etikettgenerator med DYNAMISK anpassning
# © Copyright Rickard Längkvist {get_copyright_year()} - All rights reserved
# Stöd för: SVG, EPS, PNG, JPG och andra bildformat
# Kopplar ihop: Script/label.py och Script/logotyp.py
# Export: PDF:er sparas i approtens undermapp 'export/'

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from ttkthemes import ThemedTk
import subprocess
import re

# === Importera moduler från Script-mappen ===
try:
    from Script import label as LabelModule
    from Script import logotyp as LogoModule
    print("[Import] ✓ Script/label.py laddad")
    print("[Import] ✓ Script/logotyp.py laddad")
except ImportError as e:
    try:
        import label as LabelModule
        import logotyp as LogoModule
        print("[Import] ✓ Moduler laddade från samma mapp")
    except ImportError:
        print(f"[Import] ✗ Kunde inte importera moduler: {e}")
        tk.Tk().withdraw()
        messagebox.showerror(
            "Importfel",
            f"Kunde inte importera Script-moduler:\n{e}\n\n"
            "Kontrollera att Script/label.py och Script/logotyp.py finns."
        )
        sys.exit(1)

# === Konstanter ===
BINDER_SMALL_WIDTH  = 41 * mm
BINDER_THICK_WIDTH  = 57 * mm
BINDER_HEIGHT       = 64 * mm
PDF_SIDE_MARGIN     = 10 * mm
PDF_TOP_MARGIN      = 10 * mm
PDF_SPACING         = 5 * mm
A4_WIDTH, A4_HEIGHT = A4

# === Klipplinjer (skärmärken) ===
CUT_LINE_COLOR = colors.grey   # Färg på streckade klipplinjer
CUT_LINE_WIDTH = 0.3           # Tjocklek (pt)
CUT_LINE_DASH  = (2, 2)        # Streckmönster (på, av) i pt

# Månadsnamn (svenska, treställiga, versaler) för verifikat
MONTHS_SE = ["JAN", "FEB", "MAR", "APR", "MAJ", "JUN",
             "JUL", "AUG", "SEP", "OKT", "NOV", "DEC"]

# Standard logotypmapp
DEFAULT_LOGO_FOLDER = Path(__file__).parent / "Logotyp"


# ──────────────────────────────────────────────────────────
# HJÄLPFUNKTIONER — Dynamisk copyright
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
# EXPORTMAPP — delegerar till LabelModule
# ──────────────────────────────────────────────────────────

def _get_out_path(filename: str) -> Path:
    """
    Returnerar full sökväg för en PDF i export/-mappen.

    Delegerar till LabelModule.get_export_path() som skapar
    mappen om den saknas.

    Args:
        filename: Filnamn (t.ex. "rygg_smal_Titel.pdf")

    Returns:
        Path till <approt>/export/<filename>
    """
    try:
        return LabelModule.get_export_path(filename)
    except AttributeError:
        # Fallback om äldre label.py saknar get_export_path
        fallback = Path(__file__).parent / "export"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback / filename


# ──────────────────────────────────────────────────────────
# GUI-KLASS
# ──────────────────────────────────────────────────────────

class LabelGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"Pärmetikett Generator {get_copyright_year()}")
        self.root.geometry("900x600")

        # ── Tkinter-variabler ──────────────────────────────
        self.type_var                 = tk.StringVar(value="rygg_smal")
        self.auto_shrink              = tk.BooleanVar(value=True)
        self.multi_label              = tk.BooleanVar(value=False)
        self.text_size_var            = tk.IntVar(value=16)
        self.antal_var                = tk.IntVar(value=1)

        # Verifikat
        self.verifikat_year_var       = tk.IntVar(value=get_copyright_year())
        self.verifikat_per_month_var  = tk.IntVar(value=2)

        # Klipplinjer
        self.cut_lines_var            = tk.BooleanVar(value=True)

        # Logotyp-marginal från toppen
        try:
            current     = LabelModule.get_current_settings()
            initial_top = int(round(getattr(current, "logo_min_top_margin", 5)))
        except Exception:
            initial_top = 5
        self.logo_top_px_var = tk.IntVar(value=initial_top)

        # ── Instance-attribut ──────────────────────────────
        self.prepared_logo: object     = None
        self.logo_path:     str | None = None
        self.labels_text:   list       = []

        self.setup_gui()
        self.root.bind("<Control-n>", self.add_label_hotkey)
        self.root.bind("<Command-n>",  self.add_label_hotkey)

    # ──────────────────────────────────────────────────────
    # GUI-UPPBYGGNAD
    # ──────────────────────────────────────────────────────

    def setup_gui(self) -> None:
        """Bygger hela gränssnittet med Notebook, vänster och höger panel."""

        # ── Notebook ──────────────────────────────────────
        self.notebook = ttk.Notebook(self.root)
        self.main_tab = ttk.Frame(self.notebook)
        self.help_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.main_tab, text="Generator")
        self.notebook.add(self.help_tab, text="Hjälp")
        self.notebook.pack(fill="both", expand=True)

        # ── Huvud-layout ──────────────────────────────────
        left  = ttk.Frame(self.main_tab, padding=10)
        right = ttk.Frame(self.main_tab, padding=10)
        left.pack(side="left",  fill="y")
        right.pack(side="right", expand=True, fill="both")

        # ══════════════════════════════════════════════════
        # VÄNSTER PANEL
        # ══════════════════════════════════════════════════

        # ── Etikettyp ─────────────────────────────────────
        ttk.Label(left, text="Etikettyp", font=("", 10, "bold")).pack(
            anchor="w", pady=(0, 5))
        for text, val in [
            ("Smal (41×64 mm)",  "rygg_smal"),
            ("Tjock (57×64 mm)", "rygg_tjock"),
            ("Index (A4)",       "index"),
        ]:
            ttk.Radiobutton(
                left, text=text, variable=self.type_var, value=val,
                command=lambda: self.update_label_fields(True)
            ).pack(anchor="w")

        ttk.Separator(left, orient="horizontal").pack(fill="x", pady=10)

        # ── Logotyp ───────────────────────────────────────
        ttk.Label(left, text="Logotyp", font=("", 10, "bold")).pack(
            anchor="w", pady=(0, 5))
        ttk.Button(
            left, text="📁 Välj logotyp (SVG/PNG/JPG)...",
            command=self.choose_logo
        ).pack(fill="x", pady=2)
        ttk.Button(
            left, text="📂 Öppna Logotyp-mappen",
            command=self.open_logo_folder
        ).pack(fill="x", pady=2)

        self.logo_label = ttk.Label(
            left, text="Ingen logotyp vald",
            wraplength=180, foreground="gray"
        )
        self.logo_label.pack(anchor="w", pady=(5, 0))

        # Logga från topp (px)
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

        ttk.Separator(left, orient="horizontal").pack(fill="x", pady=10)

        # ── Inställningar ─────────────────────────────────
        ttk.Label(left, text="Inställningar", font=("", 10, "bold")).pack(
            anchor="w", pady=(0, 5))

        ttk.Label(left, text="Textstorlek:").pack(anchor="w")
        size_frame = ttk.Frame(left)
        size_frame.pack(fill="x")
        ttk.Scale(
            size_frame, from_=8, to=32,
            variable=self.text_size_var, orient="horizontal"
        ).pack(side="left", fill="x", expand=True)
        ttk.Label(size_frame, textvariable=self.text_size_var, width=3).pack(
            side="right")

        ttk.Checkbutton(
            left, text="✓ Autoanpassa text",
            variable=self.auto_shrink
        ).pack(anchor="w", pady=2)
        ttk.Checkbutton(
            left, text="✓ Flera etiketter",
            variable=self.multi_label
        ).pack(anchor="w", pady=2)
        ttk.Checkbutton(
            left, text="✓ Klipplinjer (kant till kant)",
            variable=self.cut_lines_var
        ).pack(anchor="w", pady=2)

        ttk.Label(left, text="Antal etiketter:").pack(anchor="w", pady=(10, 0))
        self.antal_entry = ttk.Spinbox(
            left, from_=1, to=50,
            textvariable=self.antal_var, width=5,
            command=lambda: self.update_label_fields(True)
        )
        self.antal_entry.pack(anchor="w", pady=(0, 10))

        ttk.Separator(left, orient="horizontal").pack(fill="x", pady=10)

        # ── Skapa PDF ─────────────────────────────────────
        ttk.Button(
            left, text="📄 SKAPA PDF",
            command=self.create_pdf,
            style="Accent.TButton"
        ).pack(fill="x", pady=5)

        # Knapp: Öppna export-mapp
        ttk.Button(
            left, text="📤 Öppna Export-mappen",
            command=self.open_export_folder
        ).pack(fill="x", pady=2)

        ttk.Separator(left, orient="horizontal").pack(fill="x", pady=10)

        # ── Verifikat ─────────────────────────────────────
        ttk.Label(left, text="Verifikat", font=("", 10, "bold")).pack(
            anchor="w", pady=(0, 5))

        verifikat_frame = ttk.Frame(left)
        verifikat_frame.pack(fill="x", pady=2)
        ttk.Label(verifikat_frame, text="År:").pack(side="left")
        ttk.Spinbox(
            verifikat_frame, from_=1900, to=2200,
            textvariable=self.verifikat_year_var, width=6
        ).pack(side="left", padx=(5, 10))
        ttk.Label(verifikat_frame, text="Per mån:").pack(side="left")
        ttk.Spinbox(
            verifikat_frame, from_=1, to=12,
            textvariable=self.verifikat_per_month_var, width=4
        ).pack(side="left", padx=(5, 0))

        ttk.Button(
            left, text="🧾 GENERERA VERIFIKAT",
            command=self.create_verifikat_pdf
        ).pack(fill="x", pady=5)

        # ══════════════════════════════════════════════════
        # HÖGER PANEL — Etiketttext med scroll
        # ══════════════════════════════════════════════════
        ttk.Label(right, text="Etiketttext", font=("", 10, "bold")).pack(
            anchor="w")

        scroll_frame = ttk.Frame(right)
        scroll_frame.pack(fill="both", expand=True)

        canvas_widget    = tk.Canvas(scroll_frame)
        scrollbar        = ttk.Scrollbar(
            scroll_frame, orient="vertical", command=canvas_widget.yview)
        self.label_container = ttk.Frame(canvas_widget)

        self.label_container.bind(
            "<Configure>",
            lambda e: canvas_widget.configure(
                scrollregion=canvas_widget.bbox("all"))
        )
        canvas_widget.create_window(
            (0, 0), window=self.label_container, anchor="nw")
        canvas_widget.configure(yscrollcommand=scrollbar.set)

        canvas_widget.pack(side="left",  fill="both", expand=True)
        scrollbar.pack(    side="right", fill="y")

        # Mushjulsscroll (Windows/macOS + Linux)
        def _on_mousewheel(event):
            canvas_widget.yview_scroll(
                int(-1 * (event.delta / 120)), "units")

        def _on_mousewheel_linux(event):
            canvas_widget.yview_scroll(
                -1 if event.num == 4 else 1, "units")

        canvas_widget.bind_all("<MouseWheel>",  _on_mousewheel)
        canvas_widget.bind_all("<Button-4>",    _on_mousewheel_linux)
        canvas_widget.bind_all("<Button-5>",    _on_mousewheel_linux)

        self.update_label_fields()

        # ══════════════════════════════════════════════════
        # HJÄLP-FLIK
        # ══════════════════════════════════════════════════
        inkscape_status = (
            "✓ Installerad" if LabelModule.find_inkscape()    else "✗ Ej hittad")
        gs_status = (
            "✓ Installerad" if LabelModule.find_ghostscript() else "✗ Ej hittad")

        # Visa export-mapp i hjälptexten
        try:
            export_folder = LabelModule.get_export_folder()
        except AttributeError:
            export_folder = Path(__file__).parent / "export"

        help_txt = tk.Text(self.help_tab, wrap="word", font=("", 10))
        help_txt.insert("1.0", f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Pärmetikett Generator v2.0 (DYNAMISK)
  {get_copyright_notice()}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STÖDDA BILDFORMAT:
  • SVG (kräver Inkscape)     {inkscape_status}
  • EPS (kräver Ghostscript)  {gs_status}
  • PNG, JPG, BMP, GIF, TIFF  ✓ Inbyggt stöd

DYNAMISK ANPASSNING:
  ✓ Logotyp skalas automatiskt oavsett originalstorlek
  ✓ Text autoanpassas (fontstorlek & radbrytning)
  ✓ Balanserad layout mellan logotyp och text
  ✓ Dynamisk copyright som uppdateras varje år

KLIPPLINJER:
  ✓ Streckade skärmärken/snittlinjer i rutnät
  ✓ Går kant till kant över hela arket
  ✓ Etiketternas ram bevaras
  ✓ Kan slås av/på i Inställningar

LOGGA FRÅN TOPP (px):
  ✓ Justera hur många px logotypen placeras från toppen
  ✓ Logotypen centreras horisontellt inom marginalen
  ✓ Gäller etiketter, verifikat och index

ETIKETTYPER:
  • Rygg Smal:  41 × 64 mm (för smala pärmar)
  • Rygg Tjock: 57 × 64 mm (för tjocka pärmar)
  • Index:      12 rader på A4 med numrering

VERIFIKAT:
  • Genererar verifikat-etiketter för valt år
  • Standard: 2 lappar per månad (kan ändras 1–12)
  • Layout per lapp (fet text):
        VERIFIKAT
        MÅN          (t.ex. JAN)
        NR           (t.ex. 1)
        ÅR           (t.ex. 2026)
  • Använder vald etikettyp (smal/tjock) + vald logotyp
  • Respekterar valda marginaler och autoanpassning

EXPORT:
  • Alla PDF:er sparas i undermappen 'export/'
  • Mapp: {export_folder}
  • Knapp "📤 Öppna Export-mappen" öppnar mappen direkt

KORTKOMMANDON:
  • Ctrl+N: Lägg till nytt etikettfält
  • Mushjul: Scrolla i etikettlistan

LOGOTYPMAPP:
  {DEFAULT_LOGO_FOLDER}

INSTALLATION AV VERKTYG:
  • Inkscape:     https://inkscape.org/release/
  • Ghostscript:  https://ghostscript.com/releases/
        """)
        help_txt.config(state="disabled", bg="#f5f5f5")
        help_txt.pack(fill="both", expand=True, padx=10, pady=10)

    # ──────────────────────────────────────────────────────
    # INSTÄLLNINGSHANTERING
    # ──────────────────────────────────────────────────────

    def on_logo_top_changed(self) -> None:
        """Uppdaterar logotypens toppmarginal (px) i LabelModule."""
        try:
            value = max(0, int(self.logo_top_px_var.get()))
        except (tk.TclError, ValueError):
            return  # Halvskrivet värde — ignorera tills giltigt

        try:
            settings = LabelModule.get_current_settings()
            settings.logo_min_top_margin = value
            settings.logo_top_margin     = value
            LabelModule.set_current_settings(settings)
        except Exception as e:
            print(f"[Inställning] Kunde inte uppdatera logotyp-toppmarginal: {e}")

    # ──────────────────────────────────────────────────────
    # ETIKETTFÄLT
    # ──────────────────────────────────────────────────────

    def update_label_fields(self, preserve_content: bool = False) -> None:
        """Skapar/uppdaterar etikettfälten i höger panel."""
        previous = (
            [t.get("1.0", tk.END).strip() for t in self.labels_text]
            if preserve_content else []
        )

        for widget in self.label_container.winfo_children():
            widget.destroy()
        self.labels_text.clear()

        count = 12 if self.type_var.get() == "index" else self.antal_var.get()

        for i in range(count):
            frame = ttk.Frame(self.label_container)
            frame.pack(fill="x", pady=2, padx=5)

            ttk.Label(frame, text=f"Etikett {i + 1}:", width=10).pack(side="left")
            text = tk.Text(frame, height=2, width=40)
            text.pack(side="left", fill="x", expand=True, padx=(5, 0))

            if i < len(previous):
                text.insert("1.0", previous[i])

            self.labels_text.append(text)

    def add_label_hotkey(self, event=None) -> None:
        """Ctrl+N: Lägg till ett nytt etikettfält (max 50)."""
        if self.type_var.get() == "index":
            messagebox.showinfo("Info", "Index har alltid exakt 12 fält.")
            return
        if self.antal_var.get() < 50:
            self.antal_var.set(self.antal_var.get() + 1)
            self.update_label_fields(preserve_content=True)

    # ──────────────────────────────────────────────────────
    # LOGOTYP
    # ──────────────────────────────────────────────────────

    def open_logo_folder(self) -> None:
        """Öppnar Logotyp-mappen i OS-filhanteraren."""
        folder = DEFAULT_LOGO_FOLDER
        if not folder.exists():
            folder.mkdir(parents=True, exist_ok=True)
            print(f"[Mapp] Skapade: {folder}")
        self._open_folder_in_os(folder)

    def open_export_folder(self) -> None:
        """Öppnar export/-mappen i OS-filhanteraren."""
        try:
            folder = LabelModule.get_export_folder()
        except AttributeError:
            folder = Path(__file__).parent / "export"
            folder.mkdir(parents=True, exist_ok=True)
        self._open_folder_in_os(folder)

    def _open_folder_in_os(self, folder: Path) -> None:
        """Öppnar en mapp i OS-filhanteraren (Windows/macOS/Linux)."""
        try:
            if sys.platform.startswith("win"):
                os.startfile(folder)
            elif sys.platform.startswith("darwin"):
                subprocess.run(["open", folder])
            else:
                subprocess.run(["xdg-open", folder])
        except Exception as e:
            messagebox.showerror("Fel", f"Kunde inte öppna mappen:\n{e}")

    def choose_logo(self) -> None:
        """Väljer och laddar logotyp (SVG/EPS/PNG/JPG/…)."""
        filepath, filetype = LabelModule.select_logo_file()

        if filepath:
            self.logo_path     = filepath
            self.prepared_logo = LabelModule.load_and_resize_logo(filepath)

            if self.prepared_logo:
                filename = os.path.basename(filepath)
                size     = (f"{self.prepared_logo.size[0]}"
                            f"×{self.prepared_logo.size[1]}")
                self.logo_label.config(
                    text=f"✓ {filename}\n({size} px, {filetype})",
                    foreground="green"
                )
                print(f"[Logo] Laddad: {filename} ({filetype})")
            else:
                self.logo_label.config(
                    text="✗ Kunde inte ladda logotyp",
                    foreground="red"
                )
        else:
            self.logo_path     = None
            self.prepared_logo = None
            self.logo_label.config(text="Ingen logotyp vald", foreground="gray")

    # ──────────────────────────────────────────────────────
    # KLIPPLINJER
    # ──────────────────────────────────────────────────────

    def _draw_cut_lines(
        self,
        c:      canvas.Canvas,
        width:  float,
        height: float,
        cols:   int,
        rows:   int,
    ) -> None:
        """Ritar streckade klipplinjer kant till kant över hela arket.

        Vertikala linjer vid varje kolumns vänster/högerkant —
        hela sidans höjd (y=0 → A4_HEIGHT).

        Horisontella linjer vid varje rads övre/underkant —
        hela sidans bredd (x=0 → A4_WIDTH).

        Etiketternas egna ramar ritas separat av label.py och
        påverkas inte.
        """
        if not self.cut_lines_var.get():
            return

        c.saveState()
        c.setStrokeColor(CUT_LINE_COLOR)
        c.setLineWidth(CUT_LINE_WIDTH)
        c.setDash(CUT_LINE_DASH[0], CUT_LINE_DASH[1])

        # Vertikala linjer
        x_positions: set = set()
        for col in range(cols):
            x_left  = PDF_SIDE_MARGIN + col * (width + PDF_SPACING)
            x_right = x_left + width
            x_positions.add(round(x_left,  3))
            x_positions.add(round(x_right, 3))

        for x in sorted(x_positions):
            c.line(x, 0, x, A4_HEIGHT)

        # Horisontella linjer
        y_positions: set = set()
        for row in range(rows):
            y_top    = A4_HEIGHT - PDF_TOP_MARGIN - row * (height + PDF_SPACING)
            y_bottom = y_top - height
            y_positions.add(round(y_top,    3))
            y_positions.add(round(y_bottom, 3))

        for y in sorted(y_positions):
            c.line(0, y, A4_WIDTH, y)

        c.restoreState()

    # ──────────────────────────────────────────────────────
    # SKAPA PDF (rygg / index)
    # ──────────────────────────────────────────────────────

    def create_pdf(self) -> None:
        """Skapar PDF med autoanpassning. Sparar i export/-mappen."""
        self.on_logo_top_changed()

        label_type = self.type_var.get()
        all_texts  = [t.get("1.0", tk.END).strip() for t in self.labels_text]

        # Validering
        if label_type == "index":
            if len(all_texts) != 12:
                messagebox.showerror("Fel", "Index kräver exakt 12 etikettfält.")
                return
            texts = all_texts
        else:
            texts = (
                [t for t in all_texts if t]
                if self.multi_label.get()
                else ([all_texts[0]] if all_texts and all_texts[0] else [])
            )
            if not texts:
                messagebox.showerror("Fel", "Inga giltiga etiketter ifyllda.")
                return

        # Filnamn + sökväg i export/-mappen
        title    = (
            re.sub(r'[\\/*?:"<>|]', "", texts[0].split("\n")[0])
            [:40].replace(" ", "_") or "etikett"
        )
        filename = f"{label_type}_{title}.pdf"
        out_path = _get_out_path(filename)

        # Rita
        c = canvas.Canvas(str(out_path), pagesize=A4)
        if label_type == "index":
            self.draw_index_labels(c, texts)
        else:
            self.draw_spine_labels(c, texts)
        c.save()

        messagebox.showinfo(
            "PDF skapad",
            f"✓ {filename}\n\n"
            f"Sparad i:\n{out_path.parent}\n\n"
            f"• Logotyp och text autoanpassade\n"
            f"• {get_copyright_notice()}"
        )
        self.open_file(out_path)

    # ──────────────────────────────────────────────────────
    # VERIFIKAT
    # ──────────────────────────────────────────────────────

    def build_verifikat_texts(self, year: int, per_month: int) -> List[str]:
        """Bygger verifikat-texter för alla månader × per_month.

        Format per lapp:
            VERIFIKAT
            <MÅN>
            <NR>
            <ÅR>

        Ordning: JAN 1, JAN 2, … FEB 1, FEB 2, … DEC.
        """
        texts: List[str] = []
        for month in MONTHS_SE:
            for nr in range(1, per_month + 1):
                texts.append(f"VERIFIKAT\n{month}\n{nr}\n{year}")
        return texts

    def create_verifikat_pdf(self) -> None:
        """Skapar verifikat-PDF för valt år. Sparar i export/-mappen.

        - Etikettyp 'index' faller tillbaka till rygg_smal.
        - Använder vald logotyp, marginal och autoanpassning.
        """
        self.on_logo_top_changed()

        try:
            year = int(self.verifikat_year_var.get())
        except (tk.TclError, ValueError):
            messagebox.showerror("Fel", "Ange ett giltigt år för verifikaten.")
            return

        per_month  = max(1, min(12, int(self.verifikat_per_month_var.get())))
        label_type = self.type_var.get()
        if label_type == "index":
            label_type = "rygg_smal"

        width    = BINDER_SMALL_WIDTH if label_type == "rygg_smal" else BINDER_THICK_WIDTH
        height   = BINDER_HEIGHT
        texts    = self.build_verifikat_texts(year, per_month)
        filename = f"verifikat_{year}.pdf"
        out_path = _get_out_path(filename)

        c = canvas.Canvas(str(out_path), pagesize=A4)
        self._draw_verifikat_labels(c, texts, width, height)
        c.save()

        messagebox.showinfo(
            "Verifikat skapade",
            f"✓ {filename}\n\n"
            f"År: {year}\n"
            f"Lappar per månad: {per_month}\n"
            f"Totalt antal lappar: {len(texts)}\n\n"
            f"Sparad i:\n{out_path.parent}\n\n"
            f"• Etikettyp: {'Smal' if label_type == 'rygg_smal' else 'Tjock'}\n"
            f"• Logotyp och text autoanpassade\n"
            f"• {get_copyright_notice()}"
        )
        self.open_file(out_path)

    def _draw_verifikat_labels(
        self,
        c:      canvas.Canvas,
        texts:  List[str],
        width:  float,
        height: float,
    ) -> None:
        """Ritar verifikat-etiketter i rutnät (klipplinjer + draw_single_label)."""
        max_rows = max(1, int(
            (A4_HEIGHT - 2 * PDF_TOP_MARGIN) / (height + PDF_SPACING)))
        cols     = max(1, int(
            (A4_WIDTH  - 2 * PDF_SIDE_MARGIN) / (width  + PDF_SPACING)))
        per_page = max_rows * cols

        self._draw_cut_lines(c, width, height, cols, max_rows)

        current = 0
        for text in texts:
            if current >= per_page:
                c.showPage()
                current = 0
                self._draw_cut_lines(c, width, height, cols, max_rows)

            col = current // max_rows
            row = current %  max_rows
            x   = PDF_SIDE_MARGIN + col * (width + PDF_SPACING)
            y   = (A4_HEIGHT - PDF_TOP_MARGIN
                   - (row + 1) * height - row * PDF_SPACING)

            LabelModule.draw_single_label(
                c, x, y, width, height, text,
                prepared_logo_image=self.prepared_logo,
                base_font_name="Helvetica-Bold",
                initial_font_size=self.text_size_var.get(),
                auto_shrink_text=self.auto_shrink.get(),
            )
            current += 1

    # ──────────────────────────────────────────────────────
    # RYGGETIKETTER
    # ──────────────────────────────────────────────────────

    def draw_spine_labels(
        self, c: canvas.Canvas, texts: List[str]
    ) -> None:
        """Ritar ryggetiketter (smal/tjock) i rutnät med klipplinjer."""
        width    = (BINDER_SMALL_WIDTH
                    if self.type_var.get() == "rygg_smal"
                    else BINDER_THICK_WIDTH)
        height   = BINDER_HEIGHT
        max_rows = max(1, int(
            (A4_HEIGHT - 2 * PDF_TOP_MARGIN) / (height + PDF_SPACING)))
        cols     = max(1, int(
            (A4_WIDTH  - 2 * PDF_SIDE_MARGIN) / (width  + PDF_SPACING)))

        self._draw_cut_lines(c, width, height, cols, max_rows)

        entries = texts if self.multi_label.get() else [texts[0]]
        current = 0

        for text in entries:
            if current >= max_rows * cols:
                c.showPage()
                current = 0
                self._draw_cut_lines(c, width, height, cols, max_rows)

            col = current // max_rows
            row = current %  max_rows
            x   = PDF_SIDE_MARGIN + col * (width + PDF_SPACING)
            y   = (A4_HEIGHT - PDF_TOP_MARGIN
                   - (row + 1) * height - row * PDF_SPACING)

            LabelModule.draw_single_label(
                c, x, y, width, height, text,
                prepared_logo_image=self.prepared_logo,
                base_font_name="Helvetica-Bold",
                initial_font_size=self.text_size_var.get(),
                auto_shrink_text=self.auto_shrink.get(),
            )
            current += 1

    # ──────────────────────────────────────────────────────
    # INDEXETIKETTER
    # ──────────────────────────────────────────────────────

    def draw_index_labels(
        self, c: canvas.Canvas, texts: List[str]
    ) -> None:
        """Ritar 12 indexetiketter på A4 med klipplinjer."""
        margin_top  = PDF_TOP_MARGIN
        spacing     = 2 * mm
        height      = 18 * mm
        label_width = A4_WIDTH - 2 * PDF_SIDE_MARGIN

        # Logotyp i toppen (om vald)
        if self.prepared_logo:
            logo_h     = LabelModule.draw_logo_on_page(
                c, self.prepared_logo, "index")
            margin_top += logo_h + 5 * mm

        # Klipplinjer för index
        if self.cut_lines_var.get():
            c.saveState()
            c.setStrokeColor(CUT_LINE_COLOR)
            c.setLineWidth(CUT_LINE_WIDTH)
            c.setDash(CUT_LINE_DASH[0], CUT_LINE_DASH[1])

            x_left  = PDF_SIDE_MARGIN
            x_right = PDF_SIDE_MARGIN + label_width
            c.line(x_left,  0, x_left,  A4_HEIGHT)
            c.line(x_right, 0, x_right, A4_HEIGHT)

            for i in range(len(texts)):
                y_top    = A4_HEIGHT - margin_top - i * (height + spacing)
                y_bottom = y_top - height
                c.line(0, y_top,    A4_WIDTH, y_top)
                c.line(0, y_bottom, A4_WIDTH, y_bottom)

            c.restoreState()

        # Etiketter
        for i, text in enumerate(texts):
            y            = A4_HEIGHT - margin_top - i * (height + spacing)
            display_text = (
                f"{i + 1}. {text.strip()}" if text.strip() else f"{i + 1}."
            )
            LabelModule.draw_single_label(
                c,
                x_pos=PDF_SIDE_MARGIN,
                y_pos=y - height,
                width=label_width,
                height=height,
                text_content=display_text,
                prepared_logo_image=None,
                base_font_name="Helvetica-Bold",
                initial_font_size=12,
                auto_shrink_text=True,
            )

    # ──────────────────────────────────────────────────────
    # ÖPPNA FIL
    # ──────────────────────────────────────────────────────

    def open_file(self, path: Path) -> None:
        """Öppnar den genererade PDF-filen i OS-standardprogrammet."""
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)
            elif sys.platform.startswith("darwin"):
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("Öppningsfel", str(e))


# ──────────────────────────────────────────────────────────
# STARTFUNKTION
# ──────────────────────────────────────────────────────────

def main() -> None:
    """Startar Pärmetikett Generator."""
    print(f"\n{'=' * 50}")
    print(f"  Pärmetikett Generator {get_copyright_year()}")
    print(f"  {get_copyright_notice()}")
    print(f"{'=' * 50}\n")

    # Visa export-mapp vid start
    try:
        export_folder = LabelModule.get_export_folder()
        print(f"[Export] 📤 Mapp: {export_folder}")
    except AttributeError:
        print("[Export] ⚠ get_export_folder() ej tillgänglig i LabelModule")

    # Registrera Arial-Bold (fallback: Helvetica-Bold)
    try:
        pdfmetrics.registerFont(TTFont("Arial-Bold", "arialbd.ttf"))
        print("[Font] ✓ Arial-Bold laddad")
    except Exception:
        print("[Font] ⚠ Arial-Bold ej tillgänglig — använder Helvetica-Bold")

    # Starta GUI
    root = ThemedTk(theme="arc")
    app  = LabelGUI(root)   # noqa: F841
    root.mainloop()


if __name__ == "__main__":
    main()