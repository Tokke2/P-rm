<!-- APPNAMN: Pärmetikett Generator (Binder Label Generator) -->

# Pärmetikett Generator — SPEC

<!--
═══════════════════════════════════════════════════════════════════════════════
  © Copyright Rickard Längkvist {get_copyright_year()} - All rights reserved
  Specifikation v6.3 — Sammanslagen & uppdaterad
  Senast uppdaterad: 2026-11-25
  Status: AKTIV UTVECKLING
<!--
  v6.3 — ÄNDRINGAR (2026-11-25, v1.2.0 — loggsystem + skärm/DPI)
  ───────────────────────────────────────────────────────────────
  · §8 Loggsystem: Script/loggar.py — LogManager med applog (INFO) och
    fellog (aktiva fel, unika per kod). Åtgärdat fel tas bort automatiskt
    (resolve_error) eller manuellt (clear_errors, Loggar-fliken).
    Gårdagens poster arkiveras till Loggar/arkiv/<logg>_<datum>.jsonl;
    arkiv raderas efter 7 dagar (daily_housekeeping vid start).
  · Ny flik "Loggar" i GUI:t: fellogg-Treeview (sortera klick + flytta
    drag via Script/gui_helpers.py §10) + applogg-vy.
  · Loggningspunkter: LOGO_LOAD, LOGO_MARGIN, PDF_CREATE,
    VERIFIKAT_CREATE, ARKIVINDEX_CREATE, SETTINGS_READ/SAVE, MAPPOPEN,
    OPPNA_PDF.
  · §11 Skärm/DPI: Script/skarm.py — SetProcessDpiAwarenessContext(-4)
    (Windows, före fönstret), tk-scaling efter DPI, Segoe UI 10pt,
    startgeometri = max höjd (skärm − taskbar-reserv) + anpassad bredd
    (sparminnad) + centrerad. Fönsterikon = assets/app_logotyp_512.png.
  · Appens logotyp: assets/app_logotyp.svg (redigerbar vektor för tryck)
    + 512/128 px ikoner; knapp "Använd appens logotyp".
  · Buggfix: _render_with_pymupdf öppnar SVG via filsökväg (stream gav
    fel aspekt). Loggar/ tillagd i .gitignore.
  · Tester: tests/test_loggar_skarm.py — 56 tester totalt.
-->
<!--
  v6.2 — ÄNDRINGAR (2026-11-25, v1.1.0 — från 25-förslagslistan)
  ───────────────────────────────────────────────────────────────
  · Checkruta per etikettrad: endast ikryssade rader skrivs ut / ingår i
    arkivindex (folder.py: _included_texts()).
  · Förslag #1 Smart arkivindex: Script/arkivindex.py — A4-indexark med
    platskoder A1-01, A1-02 …; knapp "Skapa arkivindex (A4)".
  · Förslag #2 Streckkoder: Script/streckkod.py — Code 128-B (ISO 15417),
    verifierad mönstertabell; valfritt band i etikettens underkant.
  · Förslag #10 Kvartal/halvår: verifikat med period=manad|kvartal|halvar
    (Q1–Q4, H1–H2). Filnamn: verifikat_<år>_kvartal_N_per_kvartal.pdf osv.
  · Förslag #11 Flerspråkighet: månadsförkortningar se/en/no
    (MONTHS_SE/EN/NO + validate_language).
  · Förslag #16 Automatisk logotypkontrast: logotyp.estimate_luminance()
    + vit baksida bakom mörka logotyper (tröskel 0.55).
  · Förslag #22 Hörnmarkeringar: label.corner_mark_lines() — L-formade,
    förstärkta hörnmarkeringar per etikett.
  · Nya settings-nycklar (bakåtkompatibla): verifikat_period,
    verifikat_language, barcode_labels, corner_marks, logo_contrast.
  · Tester: tests/test_nya_funktioner.py (37 tester totalt).
-->

  Python: 3.12+
  UI-ramverk: Tkinter + ttkthemes (BEHÅLLS — se sektion 13)
═══════════════════════════════════════════════════════════════════════════════

  OBS: HELA denna fil är dokumentation. Allt som INTE är kod är bortkommenterat
  enligt önskemål. Ingen körbar kod finns i denna spec.

  Denna spec är skriven för att vara EXTREMT utförlig så att den kan klistras
  in i en ny chatt och ge full kontext om:
    - Vilka filer som finns
    - Vilka importer varje fil har
    - Vilka funktioner varje fil innehåller (och vad de gör)
    - Vad som är gjort och vad som är kvar
    - Kända buggar + åtgärdsplan
    - Framtidsplan
═══════════════════════════════════════════════════════════════════════════════
-->

<!--
  v6.1 — ÄNDRINGAR I DENNA OMHÄVNING (2026-11-24)
  ───────────────────────────────────────────────────────────────────────
  · PDF tillagd som logotypformat (första sidan används). Konvertering:
      PDF  : PyMuPDF → Ghostscript → Inkscape → pdftoppm
      SVG  : Inkscape → cairosvg → PyMuPDF
      EPS  : Ghostscript → Inkscape
  · Script/logotyp.py är nu single source of truth för logotypinläsning;
    de gamla funktionerna i label.py är tunna wrappers.
  · Nya filer: Script/verifikat.py (ren verifikatlogik) och
    Script/settings_store.py (settings.json). Krav: requirements.txt.
  · Knappen "Skapa BÅDA (1 & 2 per månad)" skapar verifikat för hela året
    i två PDF:er: verifikat_<år>_1_per_manad.pdf (12 lappar) och
    verifikat_<år>_2_per_manad.pdf (24 lappar). Filnamnen innehåller nu
    antalet lappar per månad. Det går fortfarande att välja 3–12/månad.
  · Rättat: typsnittsfallback, radbrytning av långa ord, sidbrytning i
    rutnät, tomma etikettlistor och toppmargin för logotyp på A4-sida.
  · Tester: tests/test_etiketter.py (python -m unittest discover -s tests).
-->



<!--
───────────────────────────────────────────────────────────────────────────────
  1. SYFTE / VAD PROGRAMMET SKA GÖRA
───────────────────────────────────────────────────────────────────────────────

  Pärmetikett Generator är ett GUI-program (Python + Tkinter/ttkthemes) som
  genererar utskriftsklara PDF-etiketter för pärmar och arkivering.

  HUVUDFUNKTIONER:
    - Skapa RYGGETIKETTER för pärmar:
        • Smal:  41 × 64 mm
        • Tjock: 57 × 64 mm
    - Skapa INDEX-etiketter (12 rader på A4 med numrering)
    - Skapa VERIFIKAT-etiketter för ett valt år:
        • Knapp för BÅDA varianterna: 1 och 2 lappar per månad
        • Övriga antal 1–12 lappar per månad går också att välja
        • Layout per lapp (fet text, en rad var):
              VERIFIKAT
              MÅN        (t.ex. JAN)
              NR         (t.ex. 1)
              ÅR         (t.ex. 2026)
        • Ordning: JAN 1, JAN 2, FEB 1, FEB 2, ... DEC
    - DYNAMISK logotyphantering:
        • Stöd för PDF, SVG, EPS, AI, PNG, JPG, BMP, GIF, TIFF
        • SVG konverteras via Inkscape
        • EPS/AI konverteras via Ghostscript (fallback Inkscape)
        • Logotyp skalas automatiskt oavsett originalstorlek
        • Logotyp CENTRERAS horisontellt inom marginalen
        • Logotyp placeras minst X px från toppen (justerbart i GUI)
    - DYNAMISK textanpassning:
        • Autoanpassad fontstorlek (krymper tills texten får plats)
        • Automatisk radbrytning
        • Centrerad text
        • Fet text (Helvetica-Bold / Arial-Bold om tillgänglig)
    - KLIPPLINJER (streckade skärmärken):
        • Kant till kant över hela arket (vertikalt + horisontellt)
        • Kan slås av/på med checkbox
        • Färg: grå, dash (2,2), tjocklek 0.3 pt
    - Justerbara marginaler (sida/topp för logotyp och text)
    - Dynamisk copyright som uppdateras med aktuellt år
    - Export: alla PDF:er sparas i undermappen 'export/'
    - Mushjulsscroll i etikettlistan

  NYA ÖNSKEMÅL (v6.0 — se sektion 9 checklista):
    - Endast 3 teman: Mörkt / Ljust / System
    - Knappar/flikar alltid tydliga och lättlästa oavsett tema (fet text)
    - Visa/dölj flikar individuellt via "Visa"-meny + högerklick
    - Mushjulsscroll överallt (✅ IMPLEMENTERAT i etikettlistan)
    - Single-instance-lock
    - Starta minimerat i systray, öppna via enkelklick
    - Ingen terminalruta ens med .py-extension
    - Alla inställningar sparas i JSON
    - Modernt och färgglatt UI, responsivt för alla fönsterstorlekar
    - INGET profil-SKAPANDE (profiler hanteras app-till-app på begäran)
───────────────────────────────────────────────────────────────────────────────
-->


<!--
───────────────────────────────────────────────────────────────────────────────
  2. MAPPSTRUKTUR (Fullständig — Faktisk + Planerad)
───────────────────────────────────────────────────────────────────────────────

  ProjektRot/
  │
  ├── folder.py                  ← HUVUD-GUI (startfil). Kör denna.
  │                                Kopplar ihop Script/label.py +
  │                                Script/logotyp.py
  │
  ├── spec.md                    ← DENNA FIL (dokumentation)
  │
  ├── settings.json              ← (PLANERAD) Alla persisterade inställningar
  │                                (tema, flik-synlighet, fönsterstorlek,
  │                                 senaste etikettyp, textstorlek,
  │                                 cut_lines, logo_top_px, verifikat, etc.)
  │
  ├── Script/                    ← Modulmapp (logik)
  │   ├── __init__.py            ← Gör Script till ett paket (SAKNAS — se bugg)
  │   ├── label.py               ← Etikett-ritlogik + marginaler + export-mapp
  │   ├── logotyp.py             ← Logotyphantering + export-mapp
  │   ├── theme_manager.py       ← (PLANERAD) Tema: dark/light/system
  │   ├── tray_manager.py        ← (PLANERAD) Systray + single-instance
  │   ├── settings_store.py      ← (PLANERAD) Läs/skriv settings.json
  │   └── ui_helpers.py          ← (PLANERAD) Visa/dölj flikar, mushjul
  │
  ├── Logotyp/                   ← Användarens logotypfiler (SVG/PNG/EPS/...)
  │                                Skapas automatiskt om den saknas.
  │
  ├── export/                    ← Genererade PDF:er sparas HÄR
  │                                Skapas automatiskt via get_export_folder().
  │                                Ex: export/rygg_smal_Titel.pdf
  │                                    export/verifikat_2026.pdf
  │
  └── Profiler/                  ← Profildata (oanvänd enl. beslut)
                                   Koden finns i label.py men används ej.

  OBS OM PROFILER:
    label.py innehåller redan kod för profilsparning (MarginSettings + JSON).
    Enligt beslut ska INGET profil-SKAPANDE byggas in i appen just nu.
    Profilkoden får ligga kvar (oanvänd) tills användaren ber om det.

  OBS OM RAMVERK:
    Tkinter + ttkthemes BEHÅLLS (se sektion 13).
    PySide6 är INTE aktuellt för detta projekt.
    Systray hanteras med pystray + Pillow (planerat).

  RADGRÄNSPOLICY:
    - Python-huvudfil:  max 1800 rader -> föreslå uppdelning
    - Hjälpfil:         max 1200 rader -> föreslå uppdelning
    - Om svaret inte ryms: dela i 2 delar med användarkommando emellan
───────────────────────────────────────────────────────────────────────────────
-->


<!--
───────────────────────────────────────────────────────────────────────────────
  3. FILÖVERSIKT — VILKEN FIL GÖR VAD (SNABBREFERENS)
───────────────────────────────────────────────────────────────────────────────

  ┌───────────────────────┬────────────────────────────────────────────────┐
  │ FIL                   │ ANSVAR                                         │
  ├───────────────────────┼────────────────────────────────────────────────┤
  │ folder.py             │ GUI (Tkinter + ttkthemes). Användarinteraktion.│
  │                       │ Bygger PDF-layout (rutnät). Startar ritning    │
  │                       │ via Script-modulerna. Innehåller:              │
  │                       │ etikettyp-val, logotyp-val, textfält           │
  │                       │ (mushjulsscroll), "Logga från topp (px)",      │
  │                       │ klipplinjer (checkbox), verifikat-sektion,     │
  │                       │ export/-mapp-knapp, hjälpflik.                 │
  ├───────────────────────┼────────────────────────────────────────────────┤
  │ Script/label.py       │ KÄRNLOGIK för ritning. Ritar enskild etikett,  │
  │                       │ ram, logotyp (centrerad + min topp-px),        │
  │                       │ autoanpassad text. MarginSettings, verktygs-   │
  │                       │ detektering, SVG/EPS-konvertering,             │
  │                       │ export-mapphantering, (oanvänd) profil-JSON.   │
  ├───────────────────────┼────────────────────────────────────────────────┤
  │ Script/logotyp.py     │ LOGOTYPHANTERING (fristående). Filväljare,     │
  │                       │ ladda/skala logotyp, konvertera SVG/EPS,       │
  │                       │ lista logotyper i mapp, centrerad              │
  │                       │ logotypposition, export-mapphantering.         │
  ├───────────────────────┼────────────────────────────────────────────────┤
  │ Script/theme_manager  │ (PLANERAD) 3 teman (dark/light/system).        │
  │ .py                   │ ttk-stilar, OS-detektering, läsbara            │
  │                       │ knapp/flik-färger (FET text).                  │
  ├───────────────────────┼────────────────────────────────────────────────┤
  │ Script/tray_manager   │ (PLANERAD) Systray-ikon. Single-instance-lock. │
  │ .py                   │ Start minimerat. Öppna via enkelklick.         │
  ├───────────────────────┼────────────────────────────────────────────────┤
  │ Script/settings_store │ (PLANERAD) Läs/skriv settings.json.            │
  │ .py                   │ Atomär skrivning, punktnotation.               │
  ├───────────────────────┼────────────────────────────────────────────────┤
  │ Script/ui_helpers.py  │ (PLANERAD) Visa/dölj flikar, mushjulsscroll,   │
  │                       │ responsiv layout, högerklick på flik.          │
  └───────────────────────┴────────────────────────────────────────────────┘

  VIKTIGT OM DUBBLETTER:
    folder.py importerar PRIMÄRT från Script/label.py (alias LabelModule).
    label.py och logotyp.py innehåller BÅDA liknande hjälpfunktioner
    (find_inkscape, convert_*, select_logo_file, load_and_resize_logo,
    compute_centered_logo_position, get_export_folder, get_export_path).
    Se KÄNDA BUGGAR (sektion 7) om risk för divergens.
───────────────────────────────────────────────────────────────────────────────
-->


<!--
───────────────────────────────────────────────────────────────────────────────
  4. DETALJERAD FIL-API — IMPORTER & FUNKTIONER PER FIL
  (Klistra in i ny chatt för att se exakt vad som ska matchas.)
───────────────────────────────────────────────────────────────────────────────


  ════════════════════════════════════════════════════════════════════════════
  4.1  folder.py   (HUVUD-GUI / STARTFIL)   ✅ IMPLEMENTERAD
  ════════════════════════════════════════════════════════════════════════════

  STATUS: ✅ Kompilerar OK. Alla funktioner implementerade.

  IMPORTER:
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
    # Moduler (primärt):
    #   from Script import label as LabelModule
    #   from Script import logotyp as LogoModule
    # Fallback:
    #   import label as LabelModule
    #   import logotyp as LogoModule

  KONSTANTER:
    BINDER_SMALL_WIDTH  = 41 * mm
    BINDER_THICK_WIDTH  = 57 * mm
    BINDER_HEIGHT       = 64 * mm
    PDF_SIDE_MARGIN     = 10 * mm
    PDF_TOP_MARGIN      = 10 * mm
    PDF_SPACING         = 5 * mm
    A4_WIDTH, A4_HEIGHT = A4
    CUT_LINE_COLOR      = colors.grey    ← klipplinje-färg
    CUT_LINE_WIDTH      = 0.3            ← tjocklek (pt)
    CUT_LINE_DASH       = (2, 2)         ← streckmönster
    MONTHS_SE           = ["JAN","FEB","MAR","APR","MAJ","JUN",
                            "JUL","AUG","SEP","OKT","NOV","DEC"]
    DEFAULT_LOGO_FOLDER = Path(__file__).parent / "Logotyp"
    SETTINGS_FILE       = Path(__file__).parent / "settings.json"
                          (PLANERAD)

  MODULFUNKTIONER (top-level):

    get_copyright_year() -> int
      # datetime.now().year

    get_copyright_notice() -> str
      # "© Copyright Rickard Längkvist <år> - All rights reserved"

    _get_out_path(filename: str) -> Path
      # Delegerar till LabelModule.get_export_path(filename).
      # Fallback: skapar <approt>/export/ manuellt om LabelModule saknar
      # get_export_path (bakåtkompatibilitet).
      # Returnerar Path till export/<filename>.

    main() -> None
      # Startbanner (50 tecken).
      # Visar export-mapp via LabelModule.get_export_folder().
      # Registrerar Arial-Bold (fallback: Helvetica-Bold).
      # ThemedTk(theme="arc") -> LabelGUI(root) -> mainloop().
      # (PLANERAT): check_single_instance() -> send_to_existing + exit.
      # (PLANERAT): hide_to_tray(root).

  KLASS: LabelGUI

    __init__(self, root: tk.Tk)
      # root.title = "Pärmetikett Generator <år>"
      # root.geometry = "900x600"
      #
      # Tkinter-variabler:
      #   type_var                 (StringVar: "rygg_smal"/"rygg_tjock"/"index")
      #   auto_shrink              (BooleanVar = True)
      #   multi_label              (BooleanVar = False)
      #   text_size_var            (IntVar = 16)
      #   antal_var                (IntVar = 1)
      #   verifikat_year_var       (IntVar = get_copyright_year())
      #   verifikat_per_month_var  (IntVar = 2)
      #   cut_lines_var            (BooleanVar = True)
      #   logo_top_px_var          (IntVar, init från LabelModule-inställningar)
      #
      # Instance-attribut:
      #   self.prepared_logo       (PIL.Image | None)
      #   self.logo_path           (str | None)
      #   self.labels_text         (List[tk.Text])
      #   self.logo_label          (ttk.Label)
      #   self.label_container     (ttk.Frame i canvas_widget)
      #   self.notebook            (ttk.Notebook)
      #   self.main_tab            (ttk.Frame)
      #   self.help_tab            (ttk.Frame)
      #   self.antal_entry         (ttk.Spinbox)
      #
      # Binder: Ctrl+N -> add_label_hotkey
      #         Command-n -> add_label_hotkey (macOS)

    setup_gui(self) -> None
      # Bygger hela gränssnittet.
      #
      # NOTEBOOK (ttk.Notebook):
      #   Tab "Generator" + Tab "Hjälp"
      #
      # VÄNSTER PANEL (ttk.Frame, padding=10):
      #   Etikettyp (Label + 3 Radiobuttons):
      #     "Smal (41×64 mm)"  -> "rygg_smal"
      #     "Tjock (57×64 mm)" -> "rygg_tjock"
      #     "Index (A4)"       -> "index"
      #     command: update_label_fields(True)
      #
      #   Separator
      #
      #   Logotyp (Label):
      #     Knapp "📁 Välj logotyp (SVG/PNG/JPG)..."  -> choose_logo
      #     Knapp "📂 Öppna Logotyp-mappen"           -> open_logo_folder
      #     self.logo_label (ttk.Label, "Ingen logotyp vald")
      #     "Logga från topp (px):" Spinbox(0–100)
      #       command: on_logo_top_changed
      #       trace_add("write"): on_logo_top_changed
      #
      #   Separator
      #
      #   Inställningar:
      #     "Textstorlek:" + Scale(8–32) + Label(värde)
      #     Checkbutton "✓ Autoanpassa text"              (auto_shrink)
      #     Checkbutton "✓ Flera etiketter"               (multi_label)
      #     Checkbutton "✓ Klipplinjer (kant till kant)"  (cut_lines_var)
      #     "Antal etiketter:" Spinbox(1–50)
      #       command: update_label_fields(True)
      #
      #   Separator
      #
      #   Knapp "📄 SKAPA PDF"            -> create_pdf
      #   Knapp "📤 Öppna Export-mappen"  -> open_export_folder
      #
      #   Separator
      #
      #   Verifikat:
      #     "År:" Spinbox(1900–2200) + "Per mån:" Spinbox(1–12)
      #     Knapp "🧾 GENERERA VERIFIKAT"  -> create_verifikat_pdf
      #
      # HÖGER PANEL (expand=True, fill="both"):
      #   Label "Etiketttext"
      #   scroll_frame (ttk.Frame):
      #     canvas_widget (tk.Canvas) + Scrollbar (vertical)
      #     self.label_container (ttk.Frame i canvas)
      #     bind <Configure> -> uppdatera scrollregion
      #   MUSHJULSSCROLL (implementerat):
      #     canvas_widget.bind_all("<MouseWheel>")   ← Windows/macOS
      #     canvas_widget.bind_all("<Button-4>")     ← Linux (upp)
      #     canvas_widget.bind_all("<Button-5>")     ← Linux (ned)
      #   update_label_fields() körs direkt
      #
      # HJÄLP-FLIK (tk.Text, disabled):
      #   Innehåller: version, copyright, bildformat-status
      #   (Inkscape/Ghostscript), dynamisk anpassning, klipplinjer,
      #   logga-från-topp, etikettyper, verifikat-info,
      #   export-mapp-sökväg, kortkommandon, logotypmapp-sökväg,
      #   installationsinfo.
      #
      # (PLANERAT):
      #   Tema-meny "Utseende" -> Mörkt/Ljust/System
      #   "Visa"-meny -> visa/dölj flikar
      #   Högerklick på flik -> "Dölj [fliknamn]"

    on_logo_top_changed(self) -> None
      # Läser logo_top_px_var (int, min 0).
      # Vid TclError/ValueError: returnerar tyst.
      # Sätter settings.logo_min_top_margin = value.
      # Sätter settings.logo_top_margin     = value.
      # Anropar LabelModule.set_current_settings(settings).

    update_label_fields(self, preserve_content: bool = False) -> None
      # Sparar ev. befintliga textvärden om preserve_content=True.
      # Förstör alla barn i label_container.
      # Skapar N textfält:
      #   count = 12 om "index", annars antal_var.get()
      #   Per fält: ttk.Frame + ttk.Label + tk.Text(h=2, w=40)
      # Återställer innehåll om preserve_content=True.

    add_label_hotkey(self, event=None) -> None
      # Om "index": visar info-dialog.
      # Annars: antal_var += 1 (max 50),
      #   update_label_fields(preserve_content=True).

    open_logo_folder(self) -> None
      # Skapar DEFAULT_LOGO_FOLDER om saknas.
      # Anropar _open_folder_in_os(folder).

    open_export_folder(self) -> None
      # Hämtar export-mapp via LabelModule.get_export_folder().
      # Fallback: <approt>/export/ (skapar vid behov).
      # Anropar _open_folder_in_os(folder).

    _open_folder_in_os(self, folder: Path) -> None
      # Windows: os.startfile(folder)
      # macOS:   subprocess.run(["open", folder])
      # Linux:   subprocess.run(["xdg-open", folder])
      # Vid fel: messagebox.showerror.

    choose_logo(self) -> None
      # LabelModule.select_logo_file() -> (filepath, filetype)
      # LabelModule.load_and_resize_logo(filepath) -> PIL.Image
      # Uppdaterar self.prepared_logo, self.logo_path, logo_label.
      # Grön text om OK, röd om fel, grå om ingen vald.

    _draw_cut_lines(self, c: canvas.Canvas, width: float, height: float,
                    cols: int, rows: int) -> None
      # Returnerar om cut_lines_var == False.
      # saveState() -> setStrokeColor/setLineWidth/setDash
      # Vertikala linjer:
      #   x = PDF_SIDE_MARGIN + col*(width+PDF_SPACING) och +width
      #   c.line(x, 0, x, A4_HEIGHT)  ← kant till kant
      # Horisontella linjer:
      #   y = A4_HEIGHT - PDF_TOP_MARGIN - row*(height+PDF_SPACING)
      #   c.line(0, y, A4_WIDTH, y)   ← kant till kant
      # restoreState()

    create_pdf(self) -> None
      # on_logo_top_changed()
      # Hämtar label_type och texter.
      # Validerar: index=12 fält, annars minst 1 ifylld.
      # Filnamn: rensas från ogiltiga tecken, max 40 tecken.
      # out_path = _get_out_path(filename)  ← export/-mappen
      # canvas.Canvas -> draw_index_labels eller draw_spine_labels
      # c.save() -> messagebox -> open_file(out_path)

    build_verifikat_texts(self, year: int, per_month: int) -> List[str]
      # Returnerar lista: "VERIFIKAT\n<MÅN>\n<NR>\n<ÅR>"
      # 12 månader × per_month, ordning: JAN 1, JAN 2, ..., DEC.

    create_verifikat_pdf(self) -> None
      # on_logo_top_changed()
      # Validerar år (TclError -> fel-dialog).
      # label_type "index" -> "rygg_smal".
      # out_path = _get_out_path(f"verifikat_{year}.pdf")
      # canvas.Canvas -> _draw_verifikat_labels -> c.save()
      # messagebox -> open_file(out_path)

    _draw_verifikat_labels(self, c: canvas.Canvas, texts: List[str],
                           width: float, height: float) -> None
      # max_rows, cols, per_page beräknas.
      # _draw_cut_lines per sida.
      # LabelModule.draw_single_label per lapp.
      # c.showPage() + _draw_cut_lines vid sida-bryt.

    draw_spine_labels(self, c: canvas.Canvas, texts: List[str]) -> None
      # width = SMALL/THICK beroende på type_var.
      # max_rows, cols beräknas.
      # _draw_cut_lines per sida.
      # LabelModule.draw_single_label per etikett.

    draw_index_labels(self, c: canvas.Canvas, texts: List[str]) -> None
      # Logotyp i toppen via LabelModule.draw_logo_on_page().
      # Klipplinjer: 2 vertikala + N horisontella (inline saveState).
      # LabelModule.draw_single_label per rad (ingen logotyp på raderna).

    open_file(self, path: Path) -> None
      # Windows: os.startfile(path)
      # macOS:   subprocess.run(["open", path])
      # Linux:   subprocess.run(["xdg-open", path])

    # === PLANERADE METODER ===
    _load_settings(self) -> None       # Läser settings.json vid start
    _save_settings(self) -> None       # Skriver settings.json
    _apply_theme(self, theme: str) -> None  # Byter tema via theme_manager
    _toggle_tab(self, tab_name: str, visible: bool) -> None
    _on_tab_right_click(self, event) -> None


  ════════════════════════════════════════════════════════════════════════════
  4.2  Script/label.py   (KÄRNLOGIK FÖR RITNING)   ✅ IMPLEMENTERAD
  ════════════════════════════════════════════════════════════════════════════

  STATUS: ✅ Kompilerar OK. Export-mapp implementerad.

  IMPORTER:
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

  KONSTANTER:
    DEFAULT_LOGO_SIDE_MARGIN   = 2
    DEFAULT_LOGO_TOP_MARGIN    = 5
    DEFAULT_TEXT_SIDE_MARGIN   = 4
    DEFAULT_TEXT_TOP_MARGIN    = 4
    DEFAULT_LOGO_TEXT_SPACING  = 3
    LOGO_MIN_TOP_MARGIN_PX     = 5
    LOGO_MAX_WIDTH_MM          = 40 * mm
    LOGO_MAX_HEIGHT_RATIO      = 0.50
    LOGO_MIN_HEIGHT_RATIO      = 0.10
    MIN_LOGO_HEIGHT_PT         = 3 * mm
    LABEL_LINE_SPACING_FACTOR  = 1.12
    LABEL_MIN_FONT_SIZE        = 4.0
    LABEL_MAX_FONT_SIZE        = 32.0
    LABEL_BORDER_COLOR         = colors.black
    LABEL_BORDER_WIDTH_PT      = 0.3 * mm
    DPI                        = 300
    MM_TO_PIXELS               = DPI / 25.4
    SVG_EXPORT_DPI_FACTOR      = 1.5
    DEFAULT_LOGO_FOLDER        = Path(__file__).parent.parent / "Logotyp"
    PROFILES_FOLDER            = Path(__file__).parent.parent / "Profiler"
    DEFAULT_PROFILE_FILE       = PROFILES_FOLDER / "default_profile.json"
    DEFAULT_EXPORT_FOLDER      = Path(__file__).parent.parent / "export"

  DATACLASS: MarginSettings
    Fält:
      logo_side_margin, logo_top_margin, text_side_margin, text_top_margin,
      logo_text_spacing, logo_max_height_ratio, logo_min_height_ratio,
      logo_min_top_margin, min_font_size, max_font_size, line_spacing,
      profile_name

    Metoder:
      to_dict()             -> dict
      from_dict(cls, data)  -> MarginSettings   [classmethod]
      save_to_file(filepath)-> bool             [JSON]
      load_from_file(cls, filepath) -> Optional [classmethod]

  GLOBAL STATE:
    _current_settings = MarginSettings()

  FUNKTIONER:

    get_export_folder() -> Path
      # Returnerar <approt>/export/, skapar vid behov.

    get_export_path(filename: str) -> Path
      # Returnerar <approt>/export/<filename>.

    get_current_settings() -> MarginSettings
    set_current_settings(settings) -> None
    reset_to_defaults() -> MarginSettings

    list_profiles() -> List[Path]       (* oanvänd enl. beslut)
    save_profile(name, settings) -> bool (* oanvänd)
    load_profile(name) -> Optional[...] (* oanvänd)
    delete_profile(name) -> bool         (* oanvänd)

    get_copyright_year() -> int
    get_copyright_notice() -> str

    find_inkscape() -> Optional[str]
    find_ghostscript() -> Optional[str]
    convert_svg_to_png(svg_path, width_px) -> Optional[str]
    convert_eps_to_png(eps_path, width_px) -> Optional[str]
    select_logo_file() -> Tuple[Optional[str], Optional[str]]
    load_and_resize_logo(filepath, max_width_mm, dpi) -> Optional[Image.Image]

    compute_centered_logo_position(logo_w, logo_h, area_x, area_y,
        area_width, area_height, min_top_margin=5, align_top=True)
        -> Tuple[float, float]
      # Centrerar horisontellt + min topp-marginal.
      # PDF-koordinater (origo nere till vänster).

    _calculate_optimal_logo_size(image, label_width, label_height,
        text_line_count, font_size, settings) -> Tuple[float, float]

    _break_text_into_lines(text_content, canvas, font_name, font_size,
        max_width) -> List[str]

    draw_logo_on_page(canvas, image, label_type="index") -> float
      # A4-logotyp. Centrerad. Topp = max(logo_min_top_margin, 15mm).
      # Returnerar höjd+marginal (pt).

    draw_single_label(canvas, x_pos, y_pos, width, height, text_content,
        prepared_logo_image=None, base_font_name="Helvetica-Bold",
        initial_font_size=12.0, auto_shrink_text=True, settings=None) -> None
      # 1. Ram
      # 2. Logotyp via compute_centered_logo_position + min 5 pt topp
      # 3. Autoanpassad, centrerad text (krympning via while-loop)

  __all__:
    copyright, export (get_export_folder, get_export_path,
    DEFAULT_EXPORT_FOLDER), verktyg, filhantering, ritfunktioner,
    inställningar, profiler (*oanvända), mappar


  ════════════════════════════════════════════════════════════════════════════
  4.3  Script/logotyp.py   (LOGOTYPHANTERING, FRISTÅENDE)   ✅ IMPLEMENTERAD
  ════════════════════════════════════════════════════════════════════════════

  STATUS: ✅ Kompilerar OK. Export-mapp implementerad.

  IMPORTER:
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

  KONSTANTER:
    LOGO_MAX_WIDTH_MM      = 50
    DPI                    = 300
    MM_TO_PIXELS           = DPI / 25.4
    SVG_EXPORT_DPI_FACTOR  = 1.5
    LOGO_MIN_TOP_MARGIN_PX = 5
    RASTER_FORMATS         = {'.png','.jpg','.jpeg','.bmp','.gif','.tiff','.tif'}
    VECTOR_FORMATS         = {'.svg','.eps','.ai'}
    ALL_FORMATS            = RASTER_FORMATS | VECTOR_FORMATS
    DEFAULT_LOGO_FOLDER    = Path(__file__).parent.parent / "Logotyp"
    DEFAULT_EXPORT_FOLDER  = Path(__file__).parent.parent / "export"

  FUNKTIONER:

    get_copyright_year() -> int
    get_copyright_notice() -> str

    get_export_folder() -> Path
      # Returnerar <approt>/export/, skapar vid behov.

    get_export_path(filename: str) -> Path
      # Returnerar <approt>/export/<filename>.

    find_inkscape() -> Optional[str]
    find_ghostscript() -> Optional[str]
    convert_svg_to_png(svg_path, width_px) -> Optional[str]
    convert_eps_to_png(eps_path, width_px) -> Optional[str]
    select_logo_file() -> Tuple[Optional[str], Optional[str]]
    load_and_resize_logo(filepath, max_width_mm=50, dpi=300)
        -> Optional[Image.Image]

    compute_centered_logo_position(logo_w, logo_h, area_x, area_y,
        area_width, area_height, min_top_margin=5, align_top=True)
        -> Tuple[float, float]
      # Identisk logik som label.py.

    list_logos_in_folder(folder=None) -> List[Path]
    check_tools() -> dict   # {"inkscape": path|None, "ghostscript": path|None}

  __all__:
    copyright, export (get_export_folder, get_export_path,
    DEFAULT_EXPORT_FOLDER), verktyg, konvertering, logotyp, konstanter


  ════════════════════════════════════════════════════════════════════════════
  4.4  Script/theme_manager.py   (PLANERAD)
  ════════════════════════════════════════════════════════════════════════════

  ANSVAR:
    3 teman (dark/light/system) för Tkinter/ttkthemes.
    Knappar/flikar alltid tydliga med FET text oavsett tema.

  PLANERADE KONSTANTER:
    VALID_THEMES = ("dark", "light", "system")
    LIGHT_COLORS: button_bg=#3D3D3D, button_fg=#000000 (FET)
                  tab_bg=#4A4A4A,    tab_fg=#000000 (FET)
    DARK_COLORS:  button_bg=#D0D0D0, button_fg=#FFFFFF (FET)
                  tab_bg=#C0C0C0,    tab_fg=#FFFFFF (FET)

  PLANERADE FUNKTIONER:
    detect_system_theme() -> str
      # Windows: winreg, macOS: defaults, Linux: gsettings/KDE
    apply_theme(root: tk.Tk, theme: str) -> None
      # Applicerar ttk-stilar, font-weight: bold på knappar/flikar.
    get_theme_colors(theme: str) -> dict


  ════════════════════════════════════════════════════════════════════════════
  4.5  Script/tray_manager.py   (PLANERAD)
  ════════════════════════════════════════════════════════════════════════════

  ANSVAR:
    Single-instance-lock. Systray-ikon. Start minimerat.

  PLANERADE BEROENDEN:
    pystray, PIL.Image, threading, socket/hashlib

  PLANERADE FUNKTIONER:
    check_single_instance(app_name) -> bool
    send_to_existing(app_name) -> bool
    create_tray_icon(root, app_name) -> None
      # Enkelklick -> show_from_tray. Högerklick -> (Visa, Avsluta).
    hide_to_tray(root) -> None    # root.withdraw()
    show_from_tray(root) -> None  # root.deiconify() + root.lift()


  ════════════════════════════════════════════════════════════════════════════
  4.6  Script/settings_store.py   (PLANERAD)
  ════════════════════════════════════════════════════════════════════════════

  ANSVAR:
    Läs/skriv settings.json atomärt. Punktnotation. Trådsäkert.

  PLANERADE FUNKTIONER:
    load_settings(filepath) -> dict
    save_settings(filepath, data) -> None  ← atomär (.tmp->rename)
    get(data, key, default=None) -> Any
    set_value(data, key, value) -> dict

  STANDARDVÄRDEN (settings.json):
    {
      "theme":           "system",
      "window":          {"x":100,"y":100,"width":900,"height":700},
      "tabs":            {"Generator":true,"Hjälp":true},
      "last_label_type": "rygg_smal",
      "last_text_size":  16,
      "logo_top_px":     5,
      "cut_lines":       true,
      "verifikat":       {"year":<aktuellt>,"per_month":2},
      "auto_shrink":     true,
      "multi_label":     false,
      "last_logo_path":  ""
    }


  ════════════════════════════════════════════════════════════════════════════
  4.7  Script/ui_helpers.py   (PLANERAD)
  ════════════════════════════════════════════════════════════════════════════

  ANSVAR:
    Visa/dölj Notebook-flikar. Mushjulsscroll (utökat). Responsiv layout.

  PLANERADE FUNKTIONER:
    bind_mousewheel(widget, canvas_or_listbox) -> None
      # Windows/macOS: <MouseWheel>
      # Linux: <Button-4>/<Button-5>
    toggle_tab(notebook, tab_name, visible) -> None
    add_tab_context_menu(notebook, on_hide_callback) -> None
      # Högerklick -> "Dölj [fliknamn]"
    make_responsive(root) -> None
      # columnconfigure/rowconfigure weight=1
───────────────────────────────────────────────────────────────────────────────
-->


<!--
───────────────────────────────────────────────────────────────────────────────
  5. ANROPSKEDJA / DATAFLÖDE
───────────────────────────────────────────────────────────────────────────────

  START:
    folder.py: main()
      -> (PLANERAT) check_single_instance() -> send_to_existing + exit
      -> LabelModule.get_export_folder()    ← visar mapp vid start
      -> pdfmetrics.registerFont(Arial-Bold) [fallback: Helvetica-Bold]
      -> ThemedTk(theme="arc")
      -> LabelGUI(root)
      -> (PLANERAT) apply_theme(root, theme_from_settings)
      -> (PLANERAT) hide_to_tray(root)     ← startar minimerat
      -> root.mainloop()

  VÄLJ LOGOTYP:
    LabelGUI.choose_logo()
      -> LabelModule.select_logo_file()         (filväljare)
      -> LabelModule.load_and_resize_logo()     (konvertering + skalning)
      -> self.prepared_logo (PIL.Image)

  ÄNDRA "Logga från topp (px)":
    LabelGUI.on_logo_top_changed()
      -> LabelModule.get_current_settings()
      -> settings.logo_min_top_margin = value
      -> settings.logo_top_margin     = value
      -> LabelModule.set_current_settings(settings)

  SKAPA PDF (rygg/index):
    LabelGUI.create_pdf()
      -> on_logo_top_changed()
      -> _get_out_path(filename)              ← export/-mappen
      -> draw_spine_labels() ELLER draw_index_labels()
           -> _draw_cut_lines() per sida
           -> LabelModule.draw_single_label() per etikett
           -> (index) LabelModule.draw_logo_on_page()
      -> c.save() -> open_file(out_path)

  SKAPA VERIFIKAT:
    LabelGUI.create_verifikat_pdf()
      -> on_logo_top_changed()
      -> _get_out_path(f"verifikat_{year}.pdf")
      -> build_verifikat_texts(year, per_month)
      -> _draw_verifikat_labels()
           -> _draw_cut_lines() per sida
           -> LabelModule.draw_single_label() per lapp
      -> c.save() -> open_file(out_path)

  LOGOTYPPLACERING (inuti draw_single_label):
    _calculate_optimal_logo_size()       -> (logo_w, logo_h)
    compute_centered_logo_position()     -> (x, y)
    canvas.drawImage(ImageReader(image), x, y, logo_w, logo_h)

  MUSHJULSSCROLL (implementerat i setup_gui):
    canvas_widget.bind_all("<MouseWheel>")  -> yview_scroll (Windows/macOS)
    canvas_widget.bind_all("<Button-4/5>")  -> yview_scroll (Linux)

  KLIPPLINJER:
    _draw_cut_lines(c, width, height, cols, rows)
      -> Vertikala: kant till kant (y=0 -> A4_HEIGHT)
      -> Horisontella: kant till kant (x=0 -> A4_WIDTH)
      -> saveState/restoreState (ej påverkar etikettritning)

  EXPORT-MAPP:
    _get_out_path(filename) -> LabelModule.get_export_path(filename)
      -> <approt>/export/<filename>
    open_export_folder() -> LabelModule.get_export_folder()
      -> _open_folder_in_os(folder)

  TEMABYTE (PLANERAT):
    LabelGUI._apply_theme(theme)
      -> ThemeManager.apply_theme(root, theme) -> _save_settings()

  FLIK-HANTERING (PLANERAT):
    LabelGUI._toggle_tab(tab_name, visible)
      -> UIHelpers.toggle_tab(notebook, ...) -> _save_settings()

  SYSTRAY (PLANERAT):
    TrayManager.create_tray_icon(root, "Pärmetikett Generator")
      -> Enkelklick: show_from_tray(root)
      -> Avsluta: root.quit()
───────────────────────────────────────────────────────────────────────────────
-->


<!--
───────────────────────────────────────────────────────────────────────────────
  6. GJORT DENNA SESSION (SAMMANFATTNING) — CHECKLISTA
───────────────────────────────────────────────────────────────────────────────

  folder.py:
    [x] Verifikat-funktion (knapp, År, Per mån, build_verifikat_texts,
        create_verifikat_pdf, _draw_verifikat_labels).
    [x] Klipplinjer: konstanter + checkbox + _draw_cut_lines() i alla
        ritmetoder (spine, verifikat, index).
    [x] "Logga från topp (px)": Spinbox + on_logo_top_changed().
    [x] Mushjulsscroll: bind_all <MouseWheel>/<Button-4>/<Button-5>.
    [x] Export/-mapp: _get_out_path() delegerar till LabelModule.
    [x] Knapp "📤 Öppna Export-mappen" + open_export_folder().
    [x] _open_folder_in_os(): DRY-hjälpmetod för mappöppning.
    [x] Hjälptext: export-mapp-sökväg, klipplinjer, mushjul.
    [x] main(): visar export-mapp vid start.

  Script/label.py:
    [x] Alla rättningar (from __future__, __all__, _current_settings, etc.).
    [x] compute_centered_logo_position() (centrering + min 5 pt topp).
    [x] MarginSettings.logo_min_top_margin.
    [x] draw_single_label(): centrerar logotyp + min 5 pt topp.
    [x] draw_logo_on_page(): centrerad + min topp.
    [x] DEFAULT_EXPORT_FOLDER, get_export_folder(), get_export_path().

  Script/logotyp.py:
    [x] Alla rättningar (from __future__, __all__, etc.).
    [x] compute_centered_logo_position() (centrering + min 5 pt topp).
    [x] LOGO_MIN_TOP_MARGIN_PX = 5.
    [x] DEFAULT_EXPORT_FOLDER, get_export_folder(), get_export_path().

  RAMVAL BESLUT:
    [x] Tkinter + ttkthemes BEHÅLLS (ej PySide6).
        Motivering: enkel verktygsdialog, noll extra installation,
        ttkthemes ger tillräckligt modernt utseende.
        Systray: pystray + darkdetect (planerat).

  NYA ÖNSKEMÅL DOKUMENTERADE (ej implementerade ännu):
    [x] 3 teman — dokumenterat i spec + planerade filer.
    [x] Feta, tydliga knappar/flikar — dokumenterat.
    [x] Visa/dölj flikar — dokumenterat.
    [x] Single-instance-lock — dokumenterat.
    [x] Systray + start minimerat — dokumenterat.
    [x] Ingen terminalruta — dokumenterat.
    [x] Alla settings i JSON — dokumenterat.
───────────────────────────────────────────────────────────────────────────────
-->


<!--
───────────────────────────────────────────────────────────────────────────────
  7. KÄNDA FEL / BUGGAR + ÅTGÄRDSPLAN — CHECKLISTA
───────────────────────────────────────────────────────────────────────────────

  [x] BUGG: Script/__init__.py saknas (åtgärdad).
      Allvar: MEDIUM
      Åtgärd: Skapa tom Script/__init__.py.

  [x] BUGG: Kodduplicering label.py ↔ logotyp.py (åtgärdad).
      Allvar: MEDIUM
      Symptom: find_inkscape, convert_*, select_logo_file,
               load_and_resize_logo, compute_centered_logo_position,
               get_export_folder, get_export_path finns i BÅDA.
      Åtgärd: Gör logotyp.py till "single source of truth";
              låt label.py importera därifrån.

  [ ] BUGG: folder.py importerar LogoModule men använder det aldrig.
      Allvar: LÅG
      Åtgärd: Ta bort importen ELLER använd LogoModule aktivt.

  [ ] BUGG: "px" i "Logga från topp" = PDF-punkter (pt, 72 dpi),
            ej fysiska pixlar @300 DPI.
      Allvar: LÅG
      Åtgärd: Bestäm enhet; lägg omräkning px->pt vid behov.

  [ ] BUGG: draw_spine_labels() kan krascha om texts är tom.
      Allvar: MEDIUM
      Åtgärd: Tomhetskontroll (create_pdf validerar mestadels — verifiera).

  [x] BUGG: Arial-Bold registreras men draw-funktioner använder
            "Helvetica-Bold".
      Allvar: LÅG
      Åtgärd: Kontrollera registrering; använd rätt font.

  [ ] BUGG: Långa rutnät kan rita utanför sidan.
      Allvar: MEDIUM
      Åtgärd: Validera rymd per rad; lägg sidbrytning.

  [ ] SAKNAS: Script/__init__.py (tom fil).
      Åtgärd: Skapa direkt.

  [ ] SAKNAS: Tema-hantering (dark/light/system).
      Allvar: HÖG
      Åtgärd: Implementera Script/theme_manager.py på order.

  [ ] SAKNAS: Single-instance-lock + systray.
      Allvar: MEDIUM
      Åtgärd: Implementera Script/tray_manager.py på order.
              Beroenden: pip install pystray darkdetect

  [ ] SAKNAS: Utökad mushjulsscroll (utanför etikettlistan).
      Allvar: LÅG (etikettlistan scrollar redan)
      Åtgärd: Implementera Script/ui_helpers.py på order.

  [ ] SAKNAS: Visa/dölj flikar via meny + högerklick.
      Allvar: MEDIUM
      Åtgärd: Implementera Script/ui_helpers.py på order.

  [x] SAKNAS: Alla settings i settings.json (delvis implementerat).
      Allvar: MEDIUM
      Åtgärd: Implementera Script/settings_store.py på order.

  [ ] BEGRÄNSNING: Ingen förhandsgranskning av etikett.
      Allvar: LÅG (Fas 4)
      Åtgärd: Rendera miniatyr i högerpanel.

  [ ] BEGRÄNSNING: Inkscape/Ghostscript krävs för SVG/EPS.
      Allvar: MEDIUM
      Åtgärd: cairosvg som SVG-fallback (pip install cairosvg).
───────────────────────────────────────────────────────────────────────────────
-->


<!--
───────────────────────────────────────────────────────────────────────────────
  8. RADGRÄNSER & HJÄLPFILSPOLICY
───────────────────────────────────────────────────────────────────────────────

  REGEL:
    - Python-huvudfil:  max 1800 rader -> föreslå uppdelning.
    - Hjälpfil:         max 1200 rader -> föreslå uppdelning.
    - Om svaret inte ryms: dela i 2 delar med kommando emellan.

  NUVARANDE STATUS (uppskattning):
    folder.py         : ~600–700 rader  -> OK
    Script/label.py   : ~800–900 rader  -> OK
    Script/logotyp.py : ~450–550 rader  -> OK

  PLANERADE NYA FILER (hjälpfiler, max 1200 rader var):
    Script/theme_manager.py   (~300 rader)
    Script/tray_manager.py    (~250 rader)
    Script/settings_store.py  (~200 rader)
    Script/ui_helpers.py      (~250 rader)
───────────────────────────────────────────────────────────────────────────────
-->


<!--
───────────────────────────────────────────────────────────────────────────────
  9. ATT IMPLEMENTERA (NYA ÖNSKEMÅL V6.0) — CHECKLISTA
  (Ingen kod skriven för dessa ännu. Implementeras på order.)
───────────────────────────────────────────────────────────────────────────────

  OMEDELBART (Fas 1 — stabilisering):
    [x] Skapa tom Script/__init__.py.
    [x] Eliminera kodduplicering (logotyp.py som källa).
    [x] Fixa font-fallback (Arial-Bold -> Helvetica-Bold).
    [x] Tomhetskontroll i draw_spine_labels.

  UI / TEMA:
    [ ] Skapa Script/theme_manager.py.
    [ ] Endast 3 teman: Mörkt / Ljust / System.
    [ ] System-tema följer OS:ets inställning automatiskt.
    [ ] Knappar/flikar:
          Ljust tema -> mörkgrå bakgrund (#3D3D3D), svart FET text.
          Mörkt tema -> ljusgrå bakgrund (#D0D0D0), vit FET text.
    [ ] Alla knappar/flikar tydliga i ALLA teman.
    [ ] Modernt, färgglatt, responsivt UI.
    [ ] Tema-meny "Utseende" -> Mörkt / Ljust / System.

  FLIKAR / NAVIGATION:
    [ ] Skapa Script/ui_helpers.py.
    [ ] Visa/dölj varje flik via "Visa"-meny (checkable).
    [ ] Högerklick på flik -> "Dölj [fliknamn]".
    [ ] Flik-synlighet sparas i settings.json.

  SCROLL:
    [ ] Utöka mushjulsscroll till alla scrollbara ytor.
        (Etikettlistan scrollar redan via bind_all.)

  SYSTRAY / INSTANS / START:
    [ ] Skapa Script/tray_manager.py.
    [ ] pip install pystray darkdetect
    [ ] Single-instance-lock (socket/lock-fil).
    [ ] Starta ALLTID minimerat i systray med passande ikon.
    [ ] Öppna fönstret via ENKELtryck på systray-ikonen.
    [ ] Start utan terminalfönster (.pyw / pythonw / PyInstaller).

  INSTÄLLNINGAR / PERSISTENS:
    [ ] Skapa Script/settings_store.py.
    [ ] Spara i settings.json: tema, flik-synlighet, fönster,
        etikettyp, textstorlek, logo_top_px, cut_lines,
        verifikat-defaults, senaste logo-sökväg.
    [ ] INGET profil-SKAPANDE (app-till-app; på begäran).

  ARBETSREGLER:
    [ ] Uppdatera ALLA filer i en mapp innan nästa mapp.
    [ ] Skriv alltid HELA filer (ej nedkortat).
    [ ] Workspace-fil alltid i kodruta (lätt att kopiera).
    [ ] Skriv ABSOLUT ingen kod utan uttrycklig order.
    [ ] Behåll ALL befintlig funktionalitet.
───────────────────────────────────────────────────────────────────────────────
-->


<!--
───────────────────────────────────────────────────────────────────────────────
  10. FRAMTIDSPLAN (ROADMAP)
───────────────────────────────────────────────────────────────────────────────

  FAS 1 — Stabilisering (PRIO HÖG, omedelbart):
    [ ] Script/__init__.py (tom).
    [ ] Eliminera kodduplicering.
    [ ] Font-fallback Arial-Bold/Helvetica-Bold.
    [ ] Tomhetskontroll + rutnät utanför sida.

  FAS 2 — UI-modernisering (PRIO HÖG):
    [ ] Script/theme_manager.py: 3 teman.
    [ ] Feta, tydliga knappar/flikar.
    [ ] Färgglatt, responsivt UI.
    [ ] Script/ui_helpers.py: Visa/dölj flikar + utökad scroll.

  FAS 3 — Drift & systemintegration (PRIO MEDIUM):
    [ ] Script/settings_store.py: settings.json.
    [ ] Script/tray_manager.py: single-instance + systray.
    [ ] Start minimerat + öppna via enkelklick.
    [ ] Start utan terminal (.pyw/pythonw/PyInstaller).

  FAS 4 — Funktionsutökning (PRIO LÅG):
    [ ] Live-förhandsgranskning i GUI.
    [ ] Fler etikettstorlekar / egna mått i GUI.
    [ ] Export till PNG-ark / etikettark med stödlinjer.
    [ ] cairosvg-fallback (minska Inkscape-beroende).
    [ ] Flerspråksstöd (SV/EN).

  FAS 5 — Distribution:
    [ ] PyInstaller --noconsole (.exe/.app).
    [ ] Auto-uppdatering / versionskontroll.
    [ ] Installer-paket (Inno Setup / dmg).
───────────────────────────────────────────────────────────────────────────────
-->


<!--
───────────────────────────────────────────────────────────────────────────────
  11. BEROENDEN / INSTALLATION
───────────────────────────────────────────────────────────────────────────────

  PYTHON-PAKET (pip install):
    reportlab        (PDF-generering)
    Pillow           (bildhantering, PIL.Image)
    ttkthemes        (ThemedTk, theme="arc")
    pystray          (PLANERAD — systray-ikon)
    darkdetect       (PLANERAD — OS-tema-detektering)
    tkinter          (medföljer Python; Linux: python3-tk)

  EXTERNA VERKTYG (valfria, för vektor):
    Inkscape    -> SVG + fallback EPS/AI. https://inkscape.org/release/
    Ghostscript -> EPS (primärt). https://ghostscript.com/releases/

  KÖRNING:
    python folder.py         ← terminal visas
    pythonw folder.py        ← Windows utan terminal
    folder.pyw               ← Windows utan terminal (byt namn)
    pyinstaller --noconsole  ← .exe/.app utan terminal
───────────────────────────────────────────────────────────────────────────────
-->


<!--
───────────────────────────────────────────────────────────────────────────────
  12. ARBETSREGLER FÖR FRAMTIDA ÄNDRINGAR (SAMMANFATTNING)
───────────────────────────────────────────────────────────────────────────────

  [ ] Skriv ALDRIG kod utan uttrycklig order.
  [ ] Vid uppdatering: skriv ut HELA filen i kodruta (ej nedkortad).
  [ ] Uppdatera ALLA filer i en mapp innan nästa mapp påbörjas.
  [ ] Workspace-fil alltid uppdaterad och i kodruta.
  [ ] Om kod > 1800 rader (py) / 1200 rader (hjälpfil): föreslå uppdelning.
  [ ] Om svaret inte ryms: dela i 2 delar med kommando emellan.
  [ ] All icke-kod ska vara bortkommenterad i denna spec.
  [ ] Behåll ALL befintlig funktionalitet vid varje ändring.
  [ ] Inget profil-SKAPANDE utan uttrycklig order (app-till-app).
  [ ] Appnamn ALLTID längst upp (före #) -> ChatAI namnger rätt.
───────────────────────────────────────────────────────────────────────────────
-->


<!--
───────────────────────────────────────────────────────────────────────────────
  13. RAMVALSBESLUT — TKINTER VS PYSIDE6
───────────────────────────────────────────────────────────────────────────────

  BESLUT: Tkinter + ttkthemes BEHÅLLS. PySide6 är INTE aktuellt.

  MOTIVERING:
    ✅ Pärmetikett Generator är en enkel verktygsdialog
    ✅ Tkinter ingår i Python — noll extra installation
    ✅ ttkthemes (arc) ger tillräckligt modernt utseende
    ✅ Befintlig kod fungerar, hög omskrivningskostnad för liten vinst
    ✅ Systray löses med pystray + darkdetect (pip install)

  PySide6 hade passat om:
    - Komplex UI med många anpassade widgets/animationer
    - Redan Qt-baserade delar i projektet
    - Krav på hög DPI-skalning på Windows (4K)

  SYSTRAY-LÖSNING MED TKINTER:
    pip install pystray darkdetect
    Script/tray_manager.py (se sektion 4.5)
───────────────────────────────────────────────────────────────────────────────
-->


<!--
───────────────────────────────────────────────────────────────────────────────
  14. KOMPLETT KOD — ALLA IMPLEMENTERADE FILER
───────────────────────────────────────────────────────────────────────────────

  Samtliga filer finns i fullständigt, kompilerat skick:

  folder.py          (~650 rader)   Tkinter GUI, klipplinjer,
                                    mushjulsscroll, export/-mapp
  Script/label.py    (~850 rader)   Ritlogik, MarginSettings,
                                    export-mapp, centrering
  Script/logotyp.py  (~500 rader)   Logotyphantering, export-mapp,
                                    centrering

  TOTALT: ~2000 rader Python-kod
          0 syntaxfel
          Alla kompilerar OK
          Export-mapp implementerad i alla tre filer
          Mushjulsscroll implementerat i folder.py
───────────────────────────────────────────────────────────────────────────────
-->