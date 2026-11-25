# Fil: Script/verifikat.py — Ren logik för verifikatetiketter
#
# Här finns ingen GUI-kod och inga externa verktyg: modulen kan därför
# användas både av folder.py och av automatiska tester.

from __future__ import annotations

import math
from typing import Any, Callable, List, Optional, Sequence, Tuple

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm


# Månadsnamn (tre bokstäver, versaler) i kalenderordning — förslag #11.
MONTHS_SE: Tuple[str, ...] = (
    "JAN", "FEB", "MAR", "APR", "MAJ", "JUN",
    "JUL", "AUG", "SEP", "OKT", "NOV", "DEC",
)
MONTHS_EN: Tuple[str, ...] = (
    "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
    "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
)
MONTHS_NO: Tuple[str, ...] = (
    "JAN", "FEB", "MAR", "APR", "MAI", "JUN",
    "JUL", "AUG", "SEP", "OKT", "NOV", "DES",
)
MONTHS_BY_LANGUAGE = {
    "se": MONTHS_SE,
    "en": MONTHS_EN,
    "no": MONTHS_NO,
}

# Periodlägen — förslag #10: månader (standard), kvartal (Q1–Q4) och
# halvår (H1–H2) utöver månaderna.
PERIOD_MODES = {
    "manad": {"labels": None, "count": 12, "word": "manad", "sv": "månader"},
    "kvartal": {"labels": ("Q1", "Q2", "Q3", "Q4"), "count": 4,
                "word": "kvartal", "sv": "kvartal"},
    "halvar": {"labels": ("H1", "H2"), "count": 2,
               "word": "halvar", "sv": "halvår"},
}
DEFAULT_PERIOD = "manad"
DEFAULT_LANGUAGE = "se"

MIN_YEAR = 1900
MAX_YEAR = 2200
MIN_PER_MONTH = 1
MAX_PER_MONTH = 12


def validate_year(year: int) -> int:
    """Returnerar ett giltigt år eller höjer ValueError."""
    try:
        value = int(year)
    except (TypeError, ValueError) as exc:
        raise ValueError("Ange ett giltigt år.") from exc
    if not MIN_YEAR <= value <= MAX_YEAR:
        raise ValueError(f"Året måste vara mellan {MIN_YEAR} och {MAX_YEAR}.")
    return value


def validate_per_month(per_month: int) -> int:
    """Returnerar antalet lappar per period (1–12) eller höjer ValueError."""
    try:
        value = int(per_month)
    except (TypeError, ValueError) as exc:
        raise ValueError("Ange ett giltigt antal lappar per månad.") from exc
    if not MIN_PER_MONTH <= value <= MAX_PER_MONTH:
        raise ValueError(
            f"Antalet lappar per månad måste vara {MIN_PER_MONTH}–{MAX_PER_MONTH}."
        )
    return value


def validate_language(language: str) -> str:
    """Returnerar en giltig språkkod ('se', 'en', 'no') eller höjer ValueError."""
    key = str(language or DEFAULT_LANGUAGE).strip().lower()
    if key not in MONTHS_BY_LANGUAGE:
        valid = ", ".join(sorted(MONTHS_BY_LANGUAGE))
        raise ValueError(f"Okänt språk {language!r} (giltiga: {valid}).")
    return key


def validate_period_mode(period: str) -> str:
    """Returnerar ett giltigt periodläge eller höjer ValueError."""
    key = str(period or DEFAULT_PERIOD).strip().lower()
    if key not in PERIOD_MODES:
        valid = ", ".join(PERIOD_MODES)
        raise ValueError(f"Okänt periodläge {period!r} (giltiga: {valid}).")
    return key


def month_names(language: str = DEFAULT_LANGUAGE) -> Tuple[str, ...]:
    """Månadsförkortningar för valt språk ('se', 'en', 'no')."""
    return MONTHS_BY_LANGUAGE[validate_language(language)]


def period_labels(
    period: str = DEFAULT_PERIOD,
    language: str = DEFAULT_LANGUAGE,
) -> Tuple[str, ...]:
    """Periodetiketter: månader (12, valt språk), kvartal (4) eller halvår (2)."""
    mode = PERIOD_MODES[validate_period_mode(period)]
    if mode["labels"] is None:
        return month_names(language)
    return mode["labels"]


def build_verifikat_texts(
    year: int,
    per_month: int,
    language: str = DEFAULT_LANGUAGE,
    period: str = DEFAULT_PERIOD,
) -> List[str]:
    """Bygger etiketttexter för hela året, period för period.

    Varje lapp innehåller fyra rader::

        VERIFIKAT
        <PERIOD>   (månad Q1..Q4 / H1..H2 beroende på periodläge)
        <NR>
        <ÅR>

    Ordningen är JAN 1, JAN 2, … FEB 1, FEB 2, … DEC (period='manad'),
    Q1 1, Q1 2, … Q4 (period='kvartal') eller H1 …, H2 … (period='halvar').
    `language` styr månadsförkortningarna ('se', 'en', 'no').
    """
    valid_year = validate_year(year)
    count = validate_per_month(per_month)
    mode = PERIOD_MODES[validate_period_mode(period)]
    months = month_names(language) if mode["labels"] is None else mode["labels"]
    return [
        f"VERIFIKAT\n{period_name}\n{nr}\n{valid_year}"
        for period_name in months
        for nr in range(1, count + 1)
    ]


def verifikat_filename(
    year: int,
    per_month: int,
    period: str = DEFAULT_PERIOD,
) -> str:
    """Filnamn som skiljer lägen: manad (som tidigare), kvartal, halvår."""
    mode = PERIOD_MODES[validate_period_mode(period)]
    valid_year = validate_year(year)
    count = validate_per_month(per_month)
    if mode["labels"] is None:
        return f"verifikat_{valid_year}_{count}_per_manad.pdf"
    return f"verifikat_{valid_year}_{mode['word']}_{count}_per_{mode['word']}.pdf"


def verifikat_variants(year: int, counts: Tuple[int, ...] = (1, 2)) -> List[Tuple[int, str]]:
    """Returnerar (antal per månad, filnamn) för de varianter som skapas."""
    return [(count, verifikat_filename(year, count)) for count in counts]


def grid_size(
    label_width: float,
    label_height: float,
    page_size: Tuple[float, float] = A4,
    side_margin: float = 10 * mm,
    top_margin: float = 10 * mm,
    spacing: float = 5 * mm,
) -> Tuple[int, int]:
    """Returnerar (kolumner, rader) som får plats på arket."""
    page_width, page_height = page_size
    cols = max(1, math.floor(
        (page_width - 2 * side_margin) / (label_width + spacing) + 1e-9
    ))
    rows = max(1, math.floor(
        (page_height - 2 * top_margin) / (label_height + spacing) + 1e-9
    ))
    return cols, rows


def draw_verifikat_labels(
    pdf_canvas: Any,
    texts: Sequence[str],
    label_width: float,
    label_height: float,
    draw_label: Callable[[Any, float, float, float, float, str], None],
    draw_cut_lines: Optional[Callable[[int, int], None]] = None,
    *,
    page_size: Tuple[float, float] = A4,
    side_margin: float = 10 * mm,
    top_margin: float = 10 * mm,
    spacing: float = 5 * mm,
) -> int:
    """Ritar alla verifikatetiketter med automatisk sidbrytning.

    `draw_label` får (canvas, x, y, bredd, höjd, text) och används för att
    rita en etikett. `draw_cut_lines` får (kolumner, rader) och anropas på
    varje ny sida. Returnerar antalet använda sidor.
    """
    if not texts:
        return 0
    page_width, page_height = page_size
    cols, rows = grid_size(
        label_width, label_height, page_size, side_margin, top_margin, spacing
    )
    per_page = cols * rows

    def start_page() -> None:
        if draw_cut_lines:
            draw_cut_lines(cols, rows)

    start_page()
    for index, text in enumerate(texts):
        if index and index % per_page == 0:
            pdf_canvas.showPage()
            start_page()

        column, row = divmod(index % per_page, rows)
        x = side_margin + column * (label_width + spacing)
        y = (page_height - top_margin
             - (row + 1) * label_height - row * spacing)
        draw_label(pdf_canvas, x, y, label_width, label_height, text)

    return math.ceil(len(texts) / per_page)


__all__ = [
    "MONTHS_SE",
    "MONTHS_EN",
    "MONTHS_NO",
    "MONTHS_BY_LANGUAGE",
    "PERIOD_MODES",
    "DEFAULT_PERIOD",
    "DEFAULT_LANGUAGE",
    "MIN_YEAR",
    "MAX_YEAR",
    "MIN_PER_MONTH",
    "MAX_PER_MONTH",
    "validate_year",
    "validate_per_month",
    "validate_language",
    "validate_period_mode",
    "month_names",
    "period_labels",
    "build_verifikat_texts",
    "verifikat_filename",
    "verifikat_variants",
    "grid_size",
    "draw_verifikat_labels",
]
