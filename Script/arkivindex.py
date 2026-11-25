# Fil: Script/arkivindex.py — Smart arkivindex (A4) med platskoder
#
# Förslag #1: auto-genererat A4-indexark med alla pärmar och platskoder
# (A1-01, A1-02 …). Ren logik + PDF-ritning, ingen GUI-kod.

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Sequence

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

DEFAULT_PREFIX = "A"
DEFAULT_PER_SHELF = 12


@dataclass
class IndexEntry:
    """En rad i arkivindexet: platskod + pärmtext."""
    platskod: str
    text: str


def build_platskod(index: int, prefix: str = DEFAULT_PREFIX,
                   per_shelf: int = DEFAULT_PER_SHELF) -> str:
    """Platskod för etikett nr *index* (0-baserad): A1-01, A1-02 …"""
    if index < 0:
        raise ValueError("Index måste vara >= 0.")
    if per_shelf < 1:
        raise ValueError("per_shelf måste vara >= 1.")
    shelf = index // per_shelf + 1
    position = index % per_shelf + 1
    return f"{prefix}{shelf}-{position:02d}"


def build_index_entries(
    labels: Sequence[str],
    prefix: str = DEFAULT_PREFIX,
    per_shelf: int = DEFAULT_PER_SHELF,
) -> List[IndexEntry]:
    """Bygger indexrader av etiketttexterna; tomma rader hoppas över.

    Varje icke-tom etikett får en platskod i ordning. Första textraden
    används som pärmnamn (kompletta texten sparas som rad 2 i PDF:en).
    """
    entries: List[IndexEntry] = []
    for label_text in labels:
        cleaned = (label_text or "").strip()
        if not cleaned:
            continue
        first_line = cleaned.split("\n")[0].strip() or cleaned
        entries.append(IndexEntry(
            platskod=build_platskod(len(entries), prefix, per_shelf),
            text=first_line,
        ))
    return entries


def arkivindex_filename(now: Optional[datetime] = None) -> str:
    """Filnamn med datum, t.ex. arkivindex_2026-01-15.pdf."""
    stamp = (now or datetime.now()).strftime("%Y-%m-%d")
    return f"arkivindex_{stamp}.pdf"


def draw_arkivindex_pdf(
    pdf_path: str | Path,
    entries: Sequence[IndexEntry],
    title: str = "Arkivindex",
    subtitle: str = "",
    rows_per_page: int = 34,
) -> Path:
    """Ritar arkivindexet som A4-PDF (tabell: Platskod | Pärm)."""
    if rows_per_page < 1:
        raise ValueError("rows_per_page måste vara >= 1.")

    path = Path(pdf_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    page_width, page_height = A4
    side_margin = 18 * mm
    top_margin = 20 * mm
    bottom_margin = 16 * mm
    row_height = (page_height - top_margin - bottom_margin) / rows_per_page

    canvas = Canvas(str(path), pagesize=A4, pageCompression=1)
    created = datetime.now().strftime("%Y-%m-%d %H:%M")

    for page_start in range(0, max(1, len(entries)), rows_per_page):
        chunk = entries[page_start:page_start + rows_per_page]

        # Sidhuvud
        canvas.setFont("Helvetica-Bold", 16)
        canvas.drawString(side_margin, page_height - top_margin, title)
        canvas.setFont("Helvetica", 9)
        info = f"Skapad {created} · {len(entries)} pärmar"
        if subtitle:
            info = f"{subtitle} · {info}"
        canvas.drawString(side_margin, page_height - top_margin - 5 * mm, info)
        if entries:
            page_info = (
                f"Sida {page_start // rows_per_page + 1} / "
                f"{max(1, -(-len(entries) // rows_per_page))}"
            )
            canvas.drawRightString(
                page_width - side_margin, page_height - top_margin - 5 * mm,
                page_info,
            )

        # Tabellhuvud
        header_y = page_height - top_margin - 12 * mm
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(side_margin, header_y, "Platskod")
        canvas.drawString(side_margin + 28 * mm, header_y, "Pärm / etikett")
        canvas.setLineWidth(0.8)
        canvas.line(side_margin, header_y - 2 * mm,
                    page_width - side_margin, header_y - 2 * mm)

        # Rader
        canvas.setFont("Helvetica", 10)
        y = header_y - row_height
        for offset, entry in enumerate(chunk):
            canvas.setFont("Helvetica-Bold", 10)
            canvas.drawString(side_margin, y + 2 * mm, entry.platskod)
            canvas.setFont("Helvetica", 10)
            text = entry.text[:70]
            canvas.drawString(side_margin + 28 * mm, y + 2 * mm, text)
            canvas.setLineWidth(0.3)
            canvas.setStrokeGray(0.75)
            canvas.line(side_margin, y, page_width - side_margin, y)
            y -= row_height

        canvas.showPage()

    canvas.save()
    return path


__all__ = [
    "IndexEntry",
    "DEFAULT_PREFIX",
    "DEFAULT_PER_SHELF",
    "build_platskod",
    "build_index_entries",
    "arkivindex_filename",
    "draw_arkivindex_pdf",
]
