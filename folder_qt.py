# Fil: folder_qt.py — Pärmetikett Generator i Qt6 (PySide6)
# © Copyright Rickard Längkvist {get_copyright_year()} - All rights reserved
#
# Samma layout och funktioner som tkinter-versionen (folder.py) men byggd
# på Qt6:
#   * Naturlig hög-DPI-skärpa (Qt6 skalar automatiskt — skarp text, §11)
#   * QSS-design i logotypens färger (djupblå #1E3A5F + orange #F6A03C)
#   * Loggar-tabell med INBYGGD sortering (klick) och kolumnflyttning
#     (dra) enligt §10
#   * Autostart vid inloggning (Script/autostart.py, pythonw — §9)
#   * Auto-uppdatering 00:00 varje dag (REQ-K4, samma som tkinter-versionen)
#   * Utan terminalfönster: starta med pythonw.exe (§9)
#
# Alla beräkningsmoduler är GUI-oberoende och återanvänds oförändrat:
#   Script/{label, logotyp, verifikat, arkivindex, streckkod, loggar,
#           skarm, updater, autostart, settings_store}.py
#
# Kör: python folder_qt.py   (kräver: python -m pip install PySide6)
# Tkinter-versionen (folder.py) finns kvar som fallback utan beroenden.

from __future__ import annotations

import os
import queue
import re
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from Script import skarm as SkarmModule

# §9: pythonw startar utan stdout/stderr — skydda print FÖRST av allt.
SkarmModule.ensure_no_console_streams()

try:
    from PySide6.QtCore import QTimer, Qt
    from PySide6.QtGui import QFont, QIcon
    from PySide6.QtWidgets import (
        QApplication, QCheckBox, QComboBox, QFileDialog, QFrame,
        QGridLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
        QMainWindow, QMessageBox, QPlainTextEdit, QPushButton,
        QRadioButton, QScrollArea, QSpinBox, QStatusBar, QTableWidget,
        QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
    )
except ImportError as exc:  # tydligt fel i stället för traceback
    raise SystemExit(
        "PySide6 saknas — installera med:\n"
        "  python -m pip install PySide6\n"
        f"(originalfel: {exc})"
    ) from exc

from Script import (
    arkivindex as ArkivindexModule,
    autostart as AutostartModule,
    label as LabelModule,
    loggar as LoggModule,
    logotyp as LogoModule,
    settings_store as SettingsModule,
    streckkod as BarcodeModule,
    updater as UpdaterModule,
    verifikat as VerifikatModule,
)

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

# ──────────────────────────────────────────────────────────
# KONSTANTER (samma som tkinter-versionen)
# ──────────────────────────────────────────────────────────
BINDER_SMALL_WIDTH = 41 * mm
BINDER_THICK_WIDTH = 57 * mm
BINDER_HEIGHT = 64 * mm
PDF_SIDE_MARGIN = 10 * mm
PDF_TOP_MARGIN = 10 * mm
PDF_SPACING = 5 * mm
A4_WIDTH, A4_HEIGHT = A4

CUT_LINE_COLOR = "#B0B7C0"        # grå klipplinje
PRIMARY = "#1E3A5F"               # logotypens djupblå
PRIMARY_LIGHT = "#2C5282"
ACCENT = "#F6A03C"                # logotypens orange
BG = "#F4F6F9"

DEFAULT_LOGO_FOLDER = Path(__file__).parent / "Logotyp"
ASSETS_FOLDER = Path(__file__).parent / "assets"
APP_LOGOTYP_SVG = ASSETS_FOLDER / "app_logotyp.svg"
APP_LOGOTYP_ICON = ASSETS_FOLDER / "app_logotyp_512.png"

VALID_LABEL_TYPES = {"rygg_smal", "rygg_tjock", "index"}

LOGO_FILE_FILTER = (
    "Logotyper (*.pdf *.svg *.eps *.ai *.png *.jpg *.jpeg *.bmp *.gif "
    "*.tiff *.tif *.webp);;Alla filer (*)"
)


def get_copyright_year() -> int:
    return datetime.now().year


def get_copyright_notice() -> str:
    return (
        f"© Copyright Rickard Längkvist {get_copyright_year()} "
        f"- All rights reserved"
    )


# ──────────────────────────────────────────────────────────
# DESIGN (QSS) — logotypens färger, tydlig och skarp
# ──────────────────────────────────────────────────────────

def build_qss() -> str:
    return f"""
QMainWindow, QWidget {{ background: {BG}; color: #1B2A3A; }}
QLabel#h1 {{ font-size: 12pt; font-weight: 700; color: {PRIMARY}; }}
QLabel#muted {{ color: #7A8797; }}
QTabWidget::pane {{
    border: 1px solid #D5DCE4; background: white;
    border-radius: 6px; top: -1px;
}}
QTabBar::tab {{
    padding: 8px 20px; background: #E8EDF3;
    border: 1px solid #D5DCE4; border-bottom: none;
    border-top-left-radius: 6px; border-top-right-radius: 6px;
}}
QTabBar::tab:selected {{
    background: white; color: {PRIMARY};
    font-weight: 600; border-bottom: 2px solid {ACCENT};
}}
QPushButton {{
    background: {PRIMARY}; color: white; border: none;
    padding: 8px 14px; border-radius: 6px;
}}
QPushButton:hover {{ background: {PRIMARY_LIGHT}; }}
QPushButton:pressed {{ background: #16283F; }}
QPushButton:disabled {{ background: #C4CFDA; }}
QPushButton#accent {{ background: {ACCENT}; color: {PRIMARY};
    font-weight: 700; }}
QPushButton#accent:hover {{ background: #FFB55C; }}
QPushButton#flat {{ background: #E8EDF3; color: {PRIMARY}; }}
QGroupBox {{
    font-weight: 600; border: 1px solid #D5DCE4;
    border-radius: 8px; margin-top: 12px; background: white;
    padding: 6px;
}}
QGroupBox::title {{
    subcontrol-origin: margin; left: 10px; right: 10px;
    color: {PRIMARY};
}}
QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QComboBox {{
    border: 1px solid #C4CFDA; border-radius: 5px;
    padding: 4px 6px; background: white;
}}
QComboBox::drop-down {{ border: none; width: 22px; }}
QTableWidget {{
    gridline-color: #E1E7EE; border: 1px solid #D5DCE4;
    background: white;
}}
QHeaderView::section {{
    background: {PRIMARY}; color: white; padding: 6px;
    border: 0; font-weight: 600;
}}
QScrollBar:vertical {{
    background: #EDF1F5; width: 10px; border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background: #C4CFDA; border-radius: 5px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {PRIMARY_LIGHT}; }}
QStatusBar {{ background: white; border-top: 1px solid #D5DCE4; }}
QCheckBox, QRadioButton {{ spacing: 7px; }}
QCheckBox::indicator, QRadioButton::indicator {{ width: 15px; height: 15px; }}
"""


# ──────────────────────────────────────────────────────────
# HUVUDFÖNSTER — samma layout som tkinter-versionen
# ──────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self, saved: Optional[dict] = None):
        super().__init__()
        self.saved = dict(saved) if saved is not None else (
            SettingsModule.load_settings()
        )
        self.setWindowTitle(
            f"Pärmetikett Generator {get_copyright_year()}"
        )
        if APP_LOGOTYP_ICON.is_file():
            self.setWindowIcon(QIcon(str(APP_LOGOTYP_ICON)))
        self.setMinimumSize(880, 620)

        # ── Lästa inställningar → widgetvärden sätts i panelerna ──
        self._label_type = self.saved.get("label_type", "rygg_smal")
        if self._label_type not in VALID_LABEL_TYPES:
            self._label_type = "rygg_smal"
        self.logo_path: Optional[str] = self.saved.get("last_logo_path") or None
        self.prepared_logo = None
        self.logo_kind = ""
        if self.logo_path and Path(self.logo_path).is_file():
            self.prepared_logo = LabelModule.load_and_resize_logo(self.logo_path)
            if not self.prepared_logo:
                self.logo_path = None

        self.label_rows: List[tuple] = []   # (QCheckBox, QPlainTextEdit)
        self._upd_thread: Optional[threading.Thread] = None
        self._auto_upd_queue: "queue.Queue[dict]" = queue.Queue()

        # ── Flikar ───────────────────────────────────────
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.generator_tab = QWidget()
        self.help_tab = QWidget()
        self.logg_tab = QWidget()
        self.tabs.addTab(self.generator_tab, "Generator")
        self.tabs.addTab(self.help_tab, "Hjälp")
        self.tabs.addTab(self.logg_tab, "Loggar")
        self.tabs.currentChanged.connect(self._on_tab_changed)

        self._build_generator_tab()
        self._build_help_tab()
        self._build_logg_tab()

        # Statusrad
        status = QLabel(
            f"{LabelModule.get_export_folder()}   ·   {get_copyright_notice()}"
        )
        status.setContentsMargins(10, 2, 10, 2)
        status_bar = QStatusBar()
        status_bar.addWidget(status)
        self.setStatusBar(status_bar)

        # ── Startgeometri: MAX HÖJD-läge + anpassad bredd (§11) ──
        screen = self.screen().availableGeometry()
        geo_str = SkarmModule.compute_start_geometry(
            screen.width(), screen.height(),
            self.saved.get("window_geometry", ""),
        )
        match = re.match(r"(\d+)x(\d+)\+(-?\d+)\+(-?\d+)", geo_str)
        if match:
            w, h, x, y = map(int, match.groups())
            self.setGeometry(x, y, w, h)

        # ── §8: loggning + daglig städning ───────────────
        housekeeping = LoggModule.logg.daily_housekeeping()
        LoggModule.logg.log_app(
            f"App startad (Qt6) (städning: {housekeeping['arkiverade']} "
            f"arkiverade, {len(housekeeping['raderade'])} arkiv raderade)"
        )

        # ── REQ-K4: tyst kontroll vid start + 00:00-schema ──
        threading.Thread(
            target=self._auto_check_updates, daemon=True
        ).start()
        if self.auto_update_checkbox.isChecked():
            self._schedule_auto_update()

    # ──────────────────────────────────────────────────────
    # GENERATOR-FLIK (samma layout: vänsterpanel + etiketter)
    # ──────────────────────────────────────────────────────

    def _build_generator_tab(self) -> None:
        layout = QHBoxLayout(self.generator_tab)
        layout.setContentsMargins(10, 10, 10, 10)

        # ── VÄNSTER PANEL (scrollbar, bred 330 som tkinter) ──
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFixedWidth(330)
        left_scroll.setFrameShape(QFrame.NoFrame)
        left = QWidget()
        left_v = QVBoxLayout(left)
        left_v.setContentsMargins(8, 8, 8, 8)
        left_v.setSpacing(6)
        left_scroll.setWidget(left)
        layout.addWidget(left_scroll)

        # Etikettyp
        type_box = QGroupBox("Etikettyp")
        type_v = QVBoxLayout(type_box)
        self.type_buttons = {}
        for text, value in (
            ("Smal (41×64 mm)", "rygg_smal"),
            ("Tjock (57×64 mm)", "rygg_tjock"),
            ("Index (A4)", "index"),
        ):
            radio = QRadioButton(text)
            radio.setChecked(value == self._label_type)
            radio.toggled.connect(
                lambda _checked: self.update_label_fields(True)
            )
            self.type_buttons[value] = radio
            type_v.addWidget(radio)
        left_v.addWidget(type_box)

        # Logotyp
        logo_box = QGroupBox("Logotyp")
        logo_v = QVBoxLayout(logo_box)
        hint = QLabel("PDF, SVG, EPS, AI, PNG, JPG …")
        hint.setObjectName("muted")
        logo_v.addWidget(hint)
        choose = QPushButton("📁 Välj logotyp (PDF/SVG/EPS…)")
        choose.clicked.connect(self.choose_logo)
        logo_v.addWidget(choose)
        use_app = QPushButton("⭐ Använd appens logotyp (vektor)")
        use_app.clicked.connect(self.use_app_logo)
        logo_v.addWidget(use_app)
        open_folder = QPushButton("📂 Öppna Logotyp-mappen")
        open_folder.clicked.connect(self.open_logo_folder)
        logo_v.addWidget(open_folder)
        self.logo_label = QLabel("Ingen logotyp vald")
        self.logo_label.setObjectName("muted")
        self.logo_label.setWordWrap(True)
        logo_v.addWidget(self.logo_label)
        clear = QPushButton("✕ Ta bort logotyp")
        clear.clicked.connect(self.clear_logo)
        logo_v.addWidget(clear)
        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Logga från topp (px):"))
        self.logo_top_spin = QSpinBox()
        self.logo_top_spin.setRange(0, 100)
        self.logo_top_spin.setValue(int(self.saved.get("logo_top_px", 5)))
        self.logo_top_spin.valueChanged.connect(self.on_logo_top_changed)
        top_row.addWidget(self.logo_top_spin)
        top_row.addStretch(1)
        logo_v.addLayout(top_row)
        left_v.addWidget(logo_box)
        self._refresh_logo_label()

        # Inställningar
        settings_box = QGroupBox("Inställningar")
        settings_v = QVBoxLayout(settings_box)
        settings_v.addWidget(QLabel("Textstorlek:"))
        size_row = QHBoxLayout()
        self.text_size_spin = QSpinBox()
        self.text_size_spin.setRange(8, 32)
        self.text_size_spin.setValue(
            int(self.saved.get("text_size", 16))
        )
        size_row.addWidget(self.text_size_spin)
        size_row.addStretch(1)
        settings_v.addLayout(size_row)

        self.auto_shrink_check = QCheckBox("Autoanpassa text")
        self.auto_shrink_check.setChecked(
            bool(self.saved.get("auto_shrink", True))
        )
        settings_v.addWidget(self.auto_shrink_check)
        self.multi_label_check = QCheckBox("Flera etiketter")
        self.multi_label_check.setChecked(
            bool(self.saved.get("multi_label", False))
        )
        settings_v.addWidget(self.multi_label_check)
        self.cut_lines_check = QCheckBox("Klipplinjer (kant till kant)")
        self.cut_lines_check.setChecked(
            bool(self.saved.get("cut_lines", True))
        )
        settings_v.addWidget(self.cut_lines_check)
        self.corner_marks_check = QCheckBox(
            "Förstärkta hörnmarkeringar (#22)"
        )
        self.corner_marks_check.setChecked(
            bool(self.saved.get("corner_marks", False))
        )
        settings_v.addWidget(self.corner_marks_check)
        self.barcode_check = QCheckBox("Streckkod (Code 128) på etiketten (#2)")
        self.barcode_check.setChecked(
            bool(self.saved.get("barcode_labels", False))
        )
        settings_v.addWidget(self.barcode_check)
        self.logo_contrast_check = QCheckBox(
            "Automatisk logotypkontrast (#16)"
        )
        self.logo_contrast_check.setChecked(
            bool(self.saved.get("logo_contrast", False))
        )
        settings_v.addWidget(self.logo_contrast_check)

        settings_v.addWidget(QLabel("Antal etiketter:"))
        self.antal_spin = QSpinBox()
        self.antal_spin.setRange(1, 50)
        self.antal_spin.setValue(int(self.saved.get("label_count", 1)))
        self.antal_spin.valueChanged.connect(
            lambda _v: self.update_label_fields(True)
        )
        settings_v.addWidget(self.antal_spin)

        create = QPushButton("📄 SKAPA PDF")
        create.setObjectName("accent")
        create.clicked.connect(self.create_pdf)
        settings_v.addWidget(create)
        arkivindex_btn = QPushButton("🗂 Skapa arkivindex (A4, platskoder) (#1)")
        arkivindex_btn.clicked.connect(self.create_arkivindex_pdf)
        settings_v.addWidget(arkivindex_btn)
        export_btn = QPushButton("📤 Öppna Export-mappen")
        export_btn.clicked.connect(self.open_export_folder)
        settings_v.addWidget(export_btn)
        upd_btn = QPushButton("⬇️ Sök uppdatering (REQ-K4)")
        upd_btn.clicked.connect(self.check_updates_clicked)
        settings_v.addWidget(upd_btn)
        self.auto_update_checkbox = QCheckBox(
            "🕒 Auto-uppdatering 00:00 varje dag"
        )
        self.auto_update_checkbox.setChecked(
            bool(self.saved.get("auto_update_daily", True))
        )
        self.auto_update_checkbox.toggled.connect(
            self._on_auto_update_toggled
        )
        settings_v.addWidget(self.auto_update_checkbox)
        self.autostart_checkbox = QCheckBox(
            "🚀 Autostart vid inloggning (utan terminal)"
        )
        self.autostart_checkbox.setChecked(
            AutostartModule.is_autostart_enabled()
        )
        self.autostart_checkbox.toggled.connect(
            self._on_autostart_toggled
        )
        settings_v.addWidget(self.autostart_checkbox)
        left_v.addWidget(settings_box)

        # Verifikat
        verifikat_box = QGroupBox("Verifikat (hela året)")
        verifikat_v = QVBoxLayout(verifikat_box)
        period_row = QHBoxLayout()
        period_row.addWidget(QLabel("Period:"))
        self.period_combo = QComboBox()
        self.period_combo.addItems(["manad", "kvartal", "halvar"])
        saved_period = str(self.saved.get("verifikat_period", "manad"))
        if saved_period in VerifikatModule.PERIOD_MODES:
            self.period_combo.setCurrentText(saved_period)
        period_row.addWidget(self.period_combo)
        period_row.addWidget(QLabel("Språk:"))
        self.language_combo = QComboBox()
        self.language_combo.addItems(["se", "en", "no"])
        saved_language = str(self.saved.get("verifikat_language", "se"))
        if saved_language in VerifikatModule.MONTHS_BY_LANGUAGE:
            self.language_combo.setCurrentText(saved_language)
        period_row.addWidget(self.language_combo)
        verifikat_v.addLayout(period_row)
        self.period_combo.currentTextChanged.connect(
            lambda _t: self._update_verifikat_info()
        )
        self.language_combo.currentTextChanged.connect(
            lambda _t: self._update_verifikat_info()
        )

        year_row = QHBoxLayout()
        year_row.addWidget(QLabel("År:"))
        self.year_spin = QSpinBox()
        self.year_spin.setRange(
            VerifikatModule.MIN_YEAR, VerifikatModule.MAX_YEAR
        )
        saved_year = int(self.saved.get("verifikat_year", 0)) or (
            get_copyright_year()
        )
        self.year_spin.setValue(saved_year)
        year_row.addWidget(self.year_spin)
        year_row.addWidget(QLabel("Lappar/mån:"))
        self.per_month_spin = QSpinBox()
        self.per_month_spin.setRange(
            VerifikatModule.MIN_PER_MONTH, VerifikatModule.MAX_PER_MONTH
        )
        self.per_month_spin.setValue(
            int(self.saved.get("verifikat_per_month", 2))
        )
        self.per_month_spin.valueChanged.connect(
            lambda _v: self._update_verifikat_info()
        )
        year_row.addWidget(self.per_month_spin)
        verifikat_v.addLayout(year_row)

        self.verifikat_info = QLabel()
        self.verifikat_info.setObjectName("muted")
        self.verifikat_info.setWordWrap(True)
        verifikat_v.addWidget(self.verifikat_info)
        self._update_verifikat_info()

        verifikat_one = QPushButton("🧾 Skapa valt antal / månad")
        verifikat_one.clicked.connect(self.create_verifikat_pdf)
        verifikat_v.addWidget(verifikat_one)
        verifikat_both = QPushButton("🧾 Skapa BÅDA (1 & 2 per månad)")
        verifikat_both.setObjectName("accent")
        verifikat_both.clicked.connect(self.create_verifikat_both)
        verifikat_v.addWidget(verifikat_both)
        left_v.addWidget(verifikat_box)
        left_v.addStretch(1)

        # ── HÖGER PANEL — etikettexter ───────────────────
        right = QWidget()
        right_v = QVBoxLayout(right)
        right_v.setContentsMargins(4, 0, 0, 0)
        right_header = QLabel("Etiketttext")
        right_header.setObjectName("h1")
        right_v.addWidget(right_header)
        rows_scroll = QScrollArea()
        rows_scroll.setWidgetResizable(True)
        rows_scroll.setFrameShape(QFrame.NoFrame)
        self.rows_container = QWidget()
        self.rows_layout = QVBoxLayout(self.rows_container)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(4)
        rows_scroll.setWidget(self.rows_container)
        right_v.addWidget(rows_scroll)
        layout.addWidget(right)

        self.update_label_fields(False)

    # ──────────────────────────────────────────────────────
    # HJÄLP-FLIK (samma text som tkinter-versionen)
    # ──────────────────────────────────────────────────────

    def _build_help_tab(self) -> None:
        layout = QVBoxLayout(self.help_tab)
        tools = LogoModule.check_tools()
        tool_text = (
            f"PyMuPDF (PDF): {'✓' if tools['pymupdf'] else '✗'}, "
            f"Ghostscript: {'✓' if tools['ghostscript'] else '✗'}, "
            f"Inkscape: {'✓' if tools['inkscape'] else '✗'}, "
            f"cairosvg: {'✓' if tools['cairosvg'] else '✗'}"
        )
        help_view = QPlainTextEdit()
        help_view.setReadOnly(True)
        help_view.setPlainText(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Pärmetikett Generator (Qt6) — {get_copyright_notice()}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LOGOTYPER:
  • PDF (första sidan), SVG, EPS, AI och raster
    (PNG, JPG, BMP, GIF, TIFF, WEBP)
  • Vektorlogotyper renderas till högupplöst PNG
  • Konverteringsverktyg: {tool_text}

ETIKETTYPER:
  • Rygg Smal:  41 × 64 mm
  • Rygg Tjock: 57 × 64 mm
  • Index:      12 rader på A4 med numrering

VERIFIKAT — HELA ÅRET:
  • Period: månader, kvartal (Q1–Q4) eller halvår (H1–H2)  [#10]
  • Språk: se / en / no styr månadsförkortningarna          [#11]
  • "Skapa BÅDA" gör verifikat_&lt;år&gt;_1_per_manad.pdf och
    verifikat_&lt;år&gt;_2_per_manad.pdf

NYA FUNKTIONER:
  • Checkruta per etikettrad — kryssa för vad som skrivs ut
  • Streckkod (Code 128-B) i etikettens underkant             [#2]
  • Förstärkta hörnmarkeringar för exakt trimning             [#22]
  • Automatisk logotypkontrast (mörka logotyper → vit baksida) [#16]
  • Arkivindex (A4) med platskoder A1-01, A1-02 …             [#1]

LOGGAR (§8):
  • Fellogg = alla AKTIVA fel; åtgärdade försvinner automatiskt
  • Manuell rensning (valda/alla) på Loggar-fliken
  • Gårdagens poster arkiveras; arkivet rensas efter 7 dagar
  • Tabellen: sortera (klick på kolumnhuvud), flytta (dra)

UPDATER (REQ-K4, §3):
  • Jämför filer (namn + sha256) mot senaste Latest-release
  • Backup tas bort FÖRST när uppdateringen verifierats
  • AUTO-UPDATERING 00:00 varje dag (tyst, loggas i apploggen)

AUTOSTART (§9):
  • 'Autostart vid inloggning' startar appen automatiskt med
    pythonw.exe — INGET terminalfönster, varken vid start eller
    skanning

SKÄRM & SKÄRPA (§11):
  • Qt6 skalar automatiskt för hög-DPI → skarp text på 4K
  • Fönstret startar i max höjd-läge med anpassad bredd

EXPORT:
  • Alla PDF:er sparas i {LabelModule.get_export_folder()}

KORTKOMMANDON:
  • Ctrl+N: nytt etikettfält
        """)
        layout.addWidget(help_view)

    # ──────────────────────────────────────────────────────
    # LOGGAR-FLIK (§8) — sortera + flytta kolumner (§10, inbyggt i Qt)
    # ──────────────────────────────────────────────────────

    def _build_logg_tab(self) -> None:
        layout = QVBoxLayout(self.logg_tab)
        layout.setContentsMargins(10, 10, 10, 10)

        fel_group = QGroupBox(
            "Fellogg — aktiva fel (åtgärdade fel försvinner automatiskt)"
        )
        fel_v = QVBoxLayout(fel_group)
        self.fel_table = QTableWidget(0, 4)
        self.fel_table.setHorizontalHeaderLabels(
            ["Tid", "Kod", "Meddelande", "Antal"]
        )
        header = self.fel_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionsMovable(True)     # §10: flytta kolumner (dra)
        self.fel_table.setSortingEnabled(True)  # §10: sortera (klick)
        self.fel_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.fel_table.verticalHeader().setVisible(False)
        fel_v.addWidget(self.fel_table)

        buttons = QHBoxLayout()
        clear_selected = QPushButton("✕ Rensa valda fel")
        clear_selected.clicked.connect(self._clear_selected_errors)
        buttons.addWidget(clear_selected)
        clear_all = QPushButton("🗑 Rensa alla")
        clear_all.clicked.connect(self._clear_all_errors)
        buttons.addWidget(clear_all)
        buttons.addStretch(1)
        refresh = QPushButton("🔄 Uppdatera")
        refresh.clicked.connect(self._refresh_loggar)
        buttons.addWidget(refresh)
        fel_v.addLayout(buttons)
        layout.addWidget(fel_group)

        app_group = QGroupBox("Applogg (senaste 100)")
        app_v = QVBoxLayout(app_group)
        self.applog_view = QPlainTextEdit()
        self.applog_view.setReadOnly(True)
        app_v.addWidget(self.applog_view)
        layout.addWidget(app_group)

        self._refresh_loggar()

    # ──────────────────────────────────────────────────────
    # ETIKETTFÄLT (samma logik som tkinter-versionen)
    # ──────────────────────────────────────────────────────

    def _label_type_value(self) -> str:
        for value, radio in self.type_buttons.items():
            if radio.isChecked():
                return value
        return "rygg_smal"

    def update_label_fields(self, preserve: bool = False) -> None:
        """Skapar/uppdaterar textfälten (med checkruta per rad)."""
        previous = (
            [editor.toPlainText().strip() for _cb, editor in self.label_rows]
            if preserve else []
        )
        previous_include = (
            [cb.isChecked() for cb, _e in self.label_rows]
            if preserve else []
        )
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.label_rows.clear()

        count = 12 if self._label_type_value() == "index" else (
            self.antal_spin.value()
        )
        for index in range(count):
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            include = QCheckBox()
            include.setChecked(
                previous_include[index] if index < len(previous_include)
                else True
            )
            row_layout.addWidget(include)
            name = QLabel(f"Etikett {index + 1}:")
            name.setMinimumWidth(88)
            row_layout.addWidget(name)
            editor = QPlainTextEdit()
            editor.setFixedHeight(44)
            if index < len(previous):
                editor.setPlainText(previous[index])
            row_layout.addWidget(editor, 1)
            self.rows_layout.addWidget(row)
            self.label_rows.append((include, editor))
        self.rows_layout.addStretch(1)

    def _included_texts(self) -> List[str]:
        """Texterna från ikryssade rader (i ordning)."""
        return [
            editor.toPlainText().strip()
            for include, editor in self.label_rows
            if include.isChecked()
        ]

    def add_label_hotkey(self) -> None:
        """Ctrl+N lägger till ett etikettfält (max 50)."""
        if self._label_type_value() == "index":
            QMessageBox.information(self, "Info", "Index har alltid exakt 12 fält.")
            return
        if self.antal_spin.value() < 50:
            self.antal_spin.setValue(self.antal_spin.value() + 1)
            self.update_label_fields(True)

    def keyPressEvent(self, event) -> None:  # noqa: N802 (Qt-API)
        if (event.modifiers() & Qt.ControlModifier) and event.key() == Qt.Key_N:
            self.add_label_hotkey()
        super().keyPressEvent(event)

    # ──────────────────────────────────────────────────────
    # INSTÄLLNINGAR (samma nycklar som tkinter-versionen)
    # ──────────────────────────────────────────────────────

    def current_settings(self) -> dict:
        settings = dict(self.saved)
        settings.update({
            "label_type": self._label_type_value(),
            "text_size": self.text_size_spin.value(),
            "auto_shrink": self.auto_shrink_check.isChecked(),
            "multi_label": self.multi_label_check.isChecked(),
            "cut_lines": self.cut_lines_check.isChecked(),
            "logo_top_px": self.logo_top_spin.value(),
            "verifikat_year": self.year_spin.value(),
            "verifikat_per_month": self.per_month_spin.value(),
            "verifikat_period": self.period_combo.currentText(),
            "verifikat_language": self.language_combo.currentText(),
            "barcode_labels": self.barcode_check.isChecked(),
            "corner_marks": self.corner_marks_check.isChecked(),
            "logo_contrast": self.logo_contrast_check.isChecked(),
            "auto_update_daily": self.auto_update_checkbox.isChecked(),
            "label_count": self.antal_spin.value(),
            "last_logo_path": self.logo_path or "",
            "window_geometry": (
                f"{self.width()}x{self.height()}+{self.x()}+{self.y()}"
            ),
        })
        return settings

    def save_settings(self) -> None:
        SettingsModule.save_settings(
            self.current_settings(), SettingsModule.SETTINGS_PATH
        )

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt-API)
        self.on_logo_top_changed(save=False)
        self.save_settings()
        LoggModule.logg.log_app("App stängd")
        super().closeEvent(event)

    def on_logo_top_changed(self, save: bool = True) -> None:
        try:
            settings = LabelModule.get_current_settings()
            settings.logo_min_top_margin = float(self.logo_top_spin.value())
            settings.logo_top_margin = float(self.logo_top_spin.value())
            LabelModule.set_current_settings(settings)
            LoggModule.logg.resolve_error("LOGO_MARGIN")
        except Exception as exc:
            LoggModule.logg.log_error(
                "LOGO_MARGIN", f"Kunde inte uppdatera logotypmarginal: {exc}"
            )
        if save:
            self.save_settings()

    # ──────────────────────────────────────────────────────
    # VERIFIKAT-INFO
    # ──────────────────────────────────────────────────────

    def _update_verifikat_info(self) -> None:
        try:
            period = VerifikatModule.validate_period_mode(
                self.period_combo.currentText()
            )
            language = VerifikatModule.validate_language(
                self.language_combo.currentText()
            )
            count = VerifikatModule.validate_per_month(
                self.per_month_spin.value()
            )
            periods = VerifikatModule.period_labels(period, language)
            word = VerifikatModule.PERIOD_MODES[period]["sv"]
            self.verifikat_info.setText(
                f"→ {len(periods) * count} lappar "
                f"({len(periods)} {word} × {count})"
            )
        except (ValueError, TypeError):
            self.verifikat_info.setText("→ Ange 1–12 lappar per månad")

    # ──────────────────────────────────────────────────────
    # LOGOTYP
    # ──────────────────────────────────────────────────────

    def _refresh_logo_label(self) -> None:
        if self.logo_path and self.prepared_logo:
            name = Path(self.logo_path).name
            size = f"{self.prepared_logo.width}×{self.prepared_logo.height}"
            self.logo_label.setText(
                f"✓ {name}\n({size} px, {self.logo_kind or 'bild'})"
            )
            self.logo_label.setStyleSheet("color: green;")
        else:
            self.logo_label.setText("Ingen logotyp vald")
            self.logo_label.setStyleSheet("color: #7A8797;")

    def choose_logo(self) -> None:
        start = str(DEFAULT_LOGO_FOLDER)
        filepath, _filter = QFileDialog.getOpenFileName(
            self, "Välj logotyp", start, LOGO_FILE_FILTER
        )
        if not filepath:
            return
        prepared = LabelModule.load_and_resize_logo(filepath)
        if not prepared:
            LoggModule.logg.log_error(
                "LOGO_LOAD", f"Kunde inte läsa {Path(filepath).name}"
            )
            QMessageBox.critical(
                self, "Logotypen kunde inte läsas",
                f"Kunde inte läsa {Path(filepath).name}.\n\n"
                "Kontrollera filen och att ett konverteringsverktyg "
                "finns installerat (se Hjälp-fliken).",
            )
            return
        self.logo_path = filepath
        self.prepared_logo = prepared
        self.logo_kind = (
            "vektor" if Path(filepath).suffix.lower()
            in LogoModule.VECTOR_FORMATS else "bild"
        )
        LoggModule.logg.resolve_error("LOGO_LOAD")
        LoggModule.logg.log_app(f"Logotyp vald: {Path(filepath).name}")
        self._refresh_logo_label()
        self.save_settings()

    def use_app_logo(self) -> None:
        if not APP_LOGOTYP_SVG.is_file():
            QMessageBox.critical(
                self, "Saknas", f"Appens logotyp finns inte: {APP_LOGOTYP_SVG}"
            )
            return
        prepared = LabelModule.load_and_resize_logo(str(APP_LOGOTYP_SVG))
        if not prepared:
            LoggModule.logg.log_error("LOGO_LOAD", "Appens logotyp kunde inte läsas")
            QMessageBox.critical(
                self, "Logotypen kunde inte läsas",
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
        try:
            if sys.platform.startswith("win"):
                os.startfile(folder)  # type: ignore[attr-defined]
            elif sys.platform.startswith("darwin"):
                import subprocess
                subprocess.run(["open", str(folder)], check=False)
            else:
                import subprocess
                subprocess.run(["xdg-open", str(folder)], check=False)
        except Exception as exc:
            LoggModule.logg.log_error("MAPPOPEN", str(exc))
            QMessageBox.critical(self, "Fel", f"Kunde inte öppna mappen:\n{exc}")

    def open_file(self, path: Path) -> None:
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform.startswith("darwin"):
                import subprocess
                subprocess.run(["open", str(path)], check=False)
            else:
                import subprocess
                subprocess.run(["xdg-open", str(path)], check=False)
        except Exception as exc:
            LoggModule.logg.log_error("OPPNA_PDF", str(exc))
            QMessageBox.critical(self, "Öppningsfel", str(exc))

    # ──────────────────────────────────────────────────────
    # KLIPPLINJER
    # ──────────────────────────────────────────────────────

    def _draw_cut_lines(self, c, width, height, cols, rows) -> None:
        if not self.cut_lines_check.isChecked():
            return
        from reportlab.lib import colors as rl_colors

        c.saveState()
        c.setStrokeColor(rl_colors.HexColor(CUT_LINE_COLOR))
        c.setLineWidth(0.3)
        c.setDash(2, 2)
        x_positions = set()
        for col in range(cols):
            x_left = PDF_SIDE_MARGIN + col * (width + PDF_SPACING)
            x_positions.add(round(x_left, 3))
            x_positions.add(round(x_left + width, 3))
        for x in sorted(x_positions):
            c.line(x, 0, x, A4_HEIGHT)
        y_positions = set()
        for row in range(rows):
            y_top = A4_HEIGHT - PDF_TOP_MARGIN - row * (height + PDF_SPACING)
            y_positions.add(round(y_top, 3))
            y_positions.add(round(y_top - height, 3))
        for y in sorted(y_positions):
            c.line(0, y, A4_WIDTH, y)
        c.restoreState()

    def _grid_size(self, width: float, height: float) -> tuple:
        return VerifikatModule.grid_size(
            width, height, A4, PDF_SIDE_MARGIN, PDF_TOP_MARGIN, PDF_SPACING
        )

    # ──────────────────────────────────────────────────────
    # SKAPA PDF (rygg/index) — samma flöde som tkinter
    # ──────────────────────────────────────────────────────

    def _barcode_text_for(self, label_text: str) -> Optional[str]:
        rows = [
            row.strip() for row in (label_text or "").split("\n") if row.strip()
        ]
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

    def create_pdf(self) -> None:
        self.on_logo_top_changed(save=False)
        label_type = self._label_type_value()
        all_texts = self._included_texts()

        if label_type == "index":
            if len(self.label_rows) != 12:
                QMessageBox.critical(
                    self, "Fel", "Index kräver exakt 12 etikettfält."
                )
                return
            texts = [t for t in all_texts if t] or [
                editor.toPlainText().strip() for _cb, editor in self.label_rows
            ]
        else:
            texts = (
                [t for t in all_texts if t]
                if self.multi_label_check.isChecked()
                else ([all_texts[0]] if all_texts and all_texts[0] else [])
            )
            if not texts:
                QMessageBox.critical(
                    self, "Fel",
                    "Inga giltiga etiketter ifyllda.\n"
                    "Kryssa för de rader som ska skrivas ut.",
                )
                return

        title = re.sub(r'[\\/*?:"<>|]', "", texts[0].split("\n")[0])[:40]
        title = title.replace(" ", "_") or "etikett"
        out_path = LabelModule.get_export_path(f"{label_type}_{title}.pdf")

        try:
            c = canvas.Canvas(str(out_path), pagesize=A4, pageCompression=1)
            if label_type == "index":
                self._draw_index_labels(c, texts)
            else:
                self._draw_spine_labels(c, texts)
            c.save()
        except Exception as exc:
            LoggModule.logg.log_error("PDF_CREATE", str(exc))
            QMessageBox.critical(
                self, "Fel", f"PDF kunde inte skapas:\n{exc}\n\nSe Loggar-fliken."
            )
            return

        LoggModule.logg.resolve_error("PDF_CREATE")
        LoggModule.logg.log_app(
            f"PDF skapad: {out_path.name} ({len(texts)} etiketter)"
        )
        self.save_settings()
        QMessageBox.information(
            self, "PDF skapad",
            f"✓ {out_path.name}\n\nSparad i:\n{out_path.parent}\n\n"
            f"{get_copyright_notice()}",
        )
        self.open_file(out_path)

    def _draw_spine_labels(self, c, texts: List[str]) -> None:
        if not texts:
            return
        width = (
            BINDER_SMALL_WIDTH if self._label_type_value() == "rygg_smal"
            else BINDER_THICK_WIDTH
        )
        height = BINDER_HEIGHT
        cols, rows = self._grid_size(width, height)
        per_page = cols * rows
        self._draw_cut_lines(c, width, height, cols, rows)
        font_name = LabelModule.get_bold_font()
        for index, text in enumerate(texts):
            if index and index % per_page == 0:
                c.showPage()
                self._draw_cut_lines(c, width, height, cols, rows)
            slot = index % per_page
            col, row = divmod(slot, rows)
            x = PDF_SIDE_MARGIN + col * (width + PDF_SPACING)
            y = (A4_HEIGHT - PDF_TOP_MARGIN - (row + 1) * height
                 - row * PDF_SPACING)
            LabelModule.draw_single_label(
                c, x, y, width, height, text,
                prepared_logo_image=self.prepared_logo,
                base_font_name=font_name,
                initial_font_size=self.text_size_spin.value(),
                auto_shrink_text=self.auto_shrink_check.isChecked(),
                barcode_text=(
                    self._barcode_text_for(text)
                    if self.barcode_check.isChecked() else None
                ),
                corner_marks=self.corner_marks_check.isChecked(),
                logo_contrast=self.logo_contrast_check.isChecked(),
            )

    def _draw_index_labels(self, c, texts: List[str]) -> None:
        from reportlab.lib import colors as rl_colors

        margin_top = PDF_TOP_MARGIN
        spacing = 2 * mm
        height = 18 * mm
        label_width = A4_WIDTH - 2 * PDF_SIDE_MARGIN
        if self.prepared_logo:
            margin_top += LabelModule.draw_logo_on_page(
                c, self.prepared_logo, "index"
            ) + 5 * mm
        if self.cut_lines_check.isChecked():
            c.saveState()
            c.setStrokeColor(rl_colors.HexColor(CUT_LINE_COLOR))
            c.setLineWidth(0.3)
            c.setDash(2, 2)
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
                corner_marks=self.corner_marks_check.isChecked(),
            )

    # ──────────────────────────────────────────────────────
    # ARKIVINDEX (#1)
    # ──────────────────────────────────────────────────────

    def create_arkivindex_pdf(self) -> Optional[Path]:
        texts = [t for t in self._included_texts() if t]
        if not texts:
            QMessageBox.critical(
                self, "Fel",
                "Inga etiketter valda.\nKryssa för de rader som ska "
                "ingå i arkivindexet.",
            )
            return None
        entries = ArkivindexModule.build_index_entries(texts)
        out_path = LabelModule.get_export_path(
            ArkivindexModule.arkivindex_filename()
        )
        try:
            ArkivindexModule.draw_arkivindex_pdf(
                out_path, entries,
                subtitle=f"Pärmetikett Generator {get_copyright_year()}",
            )
        except Exception as exc:
            LoggModule.logg.log_error("ARKIVINDEX_CREATE", str(exc))
            QMessageBox.critical(
                self, "Fel",
                f"Arkivindex kunde inte skapas:\n{exc}\n\nSe Loggar-fliken."
            )
            return None
        LoggModule.logg.resolve_error("ARKIVINDEX_CREATE")
        LoggModule.logg.log_app(
            f"Arkivindex skapat: {out_path.name} ({len(entries)} pärmar)"
        )
        self.save_settings()
        QMessageBox.information(
            self, "Arkivindex skapat",
            f"✓ {out_path.name}\n\n{len(entries)} pärmar med platskoder "
            f"({entries[0].platskod}–{entries[-1].platskod})\n\n"
            f"Sparad i:\n{out_path.parent}\n\n{get_copyright_notice()}",
        )
        self.open_file(out_path)
        return out_path

    # ──────────────────────────────────────────────────────
    # VERIFIKAT — hela året (samma flöde som tkinter)
    # ──────────────────────────────────────────────────────

    def build_verifikat_texts(self, year: int, per_month: int) -> List[str]:
        return VerifikatModule.build_verifikat_texts(
            year, per_month,
            language=self.language_combo.currentText(),
            period=self.period_combo.currentText(),
        )

    def create_verifikat_pdf(
        self, per_month: Optional[int] = None, show_message: bool = True
    ) -> Optional[Path]:
        self.on_logo_top_changed(save=False)
        try:
            year = VerifikatModule.validate_year(self.year_spin.value())
            count = VerifikatModule.validate_per_month(
                self.per_month_spin.value() if per_month is None else per_month
            )
            period = VerifikatModule.validate_period_mode(
                self.period_combo.currentText()
            )
            language = VerifikatModule.validate_language(
                self.language_combo.currentText()
            )
        except (ValueError, TypeError) as exc:
            if show_message:
                QMessageBox.critical(self, "Fel", str(exc))
            return None
        label_type = self._label_type_value()
        if label_type == "index":
            label_type = "rygg_smal"
        width = (
            BINDER_SMALL_WIDTH if label_type == "rygg_smal"
            else BINDER_THICK_WIDTH
        )
        height = BINDER_HEIGHT
        texts = self.build_verifikat_texts(year, count)
        out_path = LabelModule.get_export_path(
            VerifikatModule.verifikat_filename(year, count, period=period)
        )
        try:
            c = canvas.Canvas(str(out_path), pagesize=A4, pageCompression=1)
            self._draw_verifikat_labels(c, texts, width, height)
            c.save()
        except Exception as exc:
            LoggModule.logg.log_error("VERIFIKAT_CREATE", str(exc))
            if show_message:
                QMessageBox.critical(
                    self, "Fel",
                    f"Verifikat kunde inte skapas:\n{exc}\n\nSe Loggar-fliken."
                )
            return None
        LoggModule.logg.resolve_error("VERIFIKAT_CREATE")
        LoggModule.logg.log_app(
            f"Verifikat skapad: {out_path.name} ({len(texts)} lappar)"
        )
        self.save_settings()
        if show_message:
            word = VerifikatModule.PERIOD_MODES[period]["sv"]
            QMessageBox.information(
                self, "Verifikat skapade",
                f"✓ {out_path.name}\n\nÅr: {year}\n"
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
        self.on_logo_top_changed(save=False)
        try:
            year = VerifikatModule.validate_year(self.year_spin.value())
        except (ValueError, TypeError) as exc:
            QMessageBox.critical(self, "Fel", str(exc))
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
                self.period_combo.currentText()
            )
            language = VerifikatModule.validate_language(
                self.language_combo.currentText()
            )
        except (ValueError, TypeError):
            period = VerifikatModule.DEFAULT_PERIOD
            language = VerifikatModule.DEFAULT_LANGUAGE
        periods = VerifikatModule.period_labels(period, language)
        word = VerifikatModule.PERIOD_MODES[period]["sv"]
        details = "\n".join(
            f"• {path.name} — {len(periods) * count} lappar ({count}/{word})"
            for count, path in created
        )
        QMessageBox.information(
            self, "Verifikat för hela året skapade",
            f"✓ {len(created)} PDF:er för {year}\n\n{details}\n\n"
            f"Sparade i:\n{created[0][1].parent}\n\n"
            f"Varje PDF innehåller alla perioder i ordning.\n"
            f"{get_copyright_notice()}",
        )
        self._open_folder_in_os(created[0][1].parent)

    def _draw_verifikat_labels(self, c, texts, width, height) -> None:
        font_name = LabelModule.get_bold_font()
        corner_marks = self.corner_marks_check.isChecked()
        logo_contrast = self.logo_contrast_check.isChecked()
        use_barcode = self.barcode_check.isChecked()

        def draw_label(pdf, x, y, label_width, label_height, text) -> None:
            LabelModule.draw_single_label(
                pdf, x, y, label_width, label_height, text,
                prepared_logo_image=self.prepared_logo,
                base_font_name=font_name,
                initial_font_size=self.text_size_spin.value(),
                auto_shrink_text=self.auto_shrink_check.isChecked(),
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
            page_size=A4, side_margin=PDF_SIDE_MARGIN,
            top_margin=PDF_TOP_MARGIN, spacing=PDF_SPACING,
        )

    # ──────────────────────────────────────────────────────
    # LOGGAR-FLIK (§8)
    # ──────────────────────────────────────────────────────

    def _on_tab_changed(self, index: int) -> None:
        if self.tabs.tabText(index) == "Loggar":
            self._refresh_loggar()

    def _refresh_loggar(self) -> None:
        """Fyller felloggen (aktiva fel) och apploggvyerna."""
        self.fel_table.setSortingEnabled(False)  # korrekt ordning vid fyllning
        self.fel_table.setRowCount(0)
        for entry in LoggModule.logg.active_errors():
            row = self.fel_table.rowCount()
            self.fel_table.insertRow(row)
            for column, value in enumerate((
                entry.get("ts", ""), entry.get("kod", ""),
                entry.get("meddelande", ""), str(entry.get("antal", 1)),
            )):
                self.fel_table.setItem(row, column, QTableWidgetItem(value))
        self.fel_table.setSortingEnabled(True)
        self.applog_view.setPlainText("\n".join(
            f"{entry.get('ts', '')}  [{entry.get('nivå', 'INFO')}]  "
            f"{entry.get('meddelande', '')}"
            for entry in LoggModule.logg.recent_app(100)
        ))

    def _clear_selected_errors(self) -> None:
        rows = sorted(
            {index.row() for index in self.fel_table.selectedIndexes()},
            reverse=True,
        )
        if not rows:
            QMessageBox.information(self, "Rensa fel", "Välj först fel att rensa.")
            return
        koder = [self.fel_table.item(row, 1).text() for row in rows]
        removed = LoggModule.logg.clear_errors(koder)
        LoggModule.logg.log_app(f"{removed} fel rensade manuellt", "INFO")
        self._refresh_loggar()

    def _clear_all_errors(self) -> None:
        removed = LoggModule.logg.clear_errors(None)
        LoggModule.logg.log_app(f"Alla fel rensade ({removed} st)", "INFO")
        self._refresh_loggar()

    # ──────────────────────────────────────────────────────
    # UPDATER (REQ-K4) + AUTO-UPPDATERING 00:00
    # ──────────────────────────────────────────────────────

    def _auto_check_updates(self) -> None:
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
        if self._upd_thread is not None and self._upd_thread.is_alive():
            QMessageBox.information(
                self, "Pågår", "En uppdateringskontroll körs redan — vänta lite."
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
                QTimer.singleShot(150, poll)
                return
            self._show_update_result(result_queue.get_nowait())

        QTimer.singleShot(150, poll)

    def _show_update_result(self, result: dict) -> None:
        if result.get("ok") and result.get("uppdaterad"):
            QMessageBox.information(
                self, "Uppdatering klar ✅",
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
            QMessageBox.information(
                self, "Ingen uppdatering behövs",
                result.get("meddelande", "Du har redan senaste versionen."),
            )
        else:
            LoggModule.logg.log_error(
                "UPD_APPLY", result.get("fel", "Okänt uppdateringsfel")
            )
            QMessageBox.critical(
                self, "Uppdatering misslyckades",
                f"{result.get('fel', 'Okänt fel')}\n\n"
                f"Se Loggar-fliken för detaljer.",
            )

    def _on_auto_update_toggled(self) -> None:
        self.save_settings()
        if self.auto_update_checkbox.isChecked():
            LoggModule.logg.log_app("Auto-uppdatering 00:00 påslagen")
            self._schedule_auto_update()
        else:
            LoggModule.logg.log_app("Auto-uppdatering 00:00 avslagen")

    def _schedule_auto_update(self) -> None:
        """Schemalägger nästa 00:00-auto-uppdatering (uppcatchning = nu)."""
        if not self.auto_update_checkbox.isChecked():
            return
        delay_ms = UpdaterModule.next_midnight_delay()
        QTimer.singleShot(max(1000, delay_ms), self._trigger_auto_update)

    def _trigger_auto_update(self) -> None:
        if not self.auto_update_checkbox.isChecked():
            return
        threading.Thread(
            target=lambda: self._auto_upd_queue.put(
                UpdaterModule.auto_update()
            ),
            daemon=True,
        ).start()
        QTimer.singleShot(300, self._poll_auto_update)

    def _poll_auto_update(self) -> None:
        if self._auto_upd_queue.empty():
            QTimer.singleShot(300, self._poll_auto_update)
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

    # ──────────────────────────────────────────────────────
    # AUTOSTART (§9) — startar vid inloggning, utan terminal
    # ──────────────────────────────────────────────────────

    def _on_autostart_toggled(self) -> None:
        if self.autostart_checkbox.isChecked():
            ok = AutostartModule.enable_autostart(
                script_path=str(Path(__file__).resolve())
            )
            if ok:
                LoggModule.logg.log_app(
                    "Autostart påslagen: "
                    f"{AutostartModule.get_autostart_command()}"
                )
            else:
                LoggModule.logg.log_error(
                    "AUTOSTART", "Autostart kunde inte slås på (endast Windows)."
                )
        else:
            ok = AutostartModule.disable_autostart()
            LoggModule.logg.log_app(
                f"Autostart {'avslagen' if ok else 'kunde inte tas bort'}"
            )


# ──────────────────────────────────────────────────────────
# STARTFUNKTION
# ──────────────────────────────────────────────────────────

def main() -> None:
    """Startar Pärmetikett Generator (Qt6)."""
    LabelModule.register_preferred_bold_font()
    saved = SettingsModule.load_settings()
    app = QApplication(sys.argv)
    app.setApplicationName("Pärmetikett Generator")
    app.setStyleSheet(build_qss())
    if sys.platform.startswith("win"):
        app.setFont(QFont("Segoe UI", 10))
    window = MainWindow(saved)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
