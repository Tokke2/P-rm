# Fil: Script/streckkod.py — Code 128-B streckkod (ren logik + PDF-ritning)
#
# Implementerar symbologin Code 128 (ISO/IEC 15417), koduppsättning B,
# utan externa beroenden. Mönstertabellen är verifierad mot Wikipedia/
# ISO-specifikationen (Start B = 211214, Stop = 2331112, 'A' = 111323).
# Modulen har ingen GUI-kod och kan användas både av folder.py och tester.

from __future__ import annotations

from typing import List, Optional, Sequence

from reportlab.lib import colors

# Mönstertabell: index = symbolvärde (0–106), värde = 6 run-längder
# (bar/space växlande, börjar med bar). Summan är alltid 11 moduler.
# Index 103–105 är Start A/B/C och 106 är Stop (utan slutbar).
CODE128_PATTERNS: tuple = (
    "212222", "222122", "222221", "121223", "121322", "131222",
    "122213", "122312", "132212", "221213", "221312", "231212",
    "112232", "122132", "122231", "113222", "123122", "123221",
    "223211", "221132", "221231", "213212", "223112", "312131",
    "311222", "321122", "321221", "312212", "322112", "322211",
    "212123", "212321", "232121", "111323", "131123", "131321",
    "112313", "132113", "132311", "211313", "231113", "231311",
    "112133", "112331", "132131", "113123", "113321", "133121",
    "313121", "211331", "231131", "213113", "213311", "213131",
    "311123", "311321", "331121", "312113", "312311", "332111",
    "314111", "221411", "431111", "111224", "111422", "121124",
    "121421", "141122", "141221", "112214", "112412", "122114",
    "122411", "142112", "142211", "241211", "221114", "413111",
    "241112", "134111", "111242", "121142", "121241", "114212",
    "124112", "124211", "411212", "421112", "421211", "212141",
    "214121", "412121", "111143", "111341", "131141", "114113",
    "114311", "411113", "411311", "113141", "114131", "311141",
    "411131", "211412", "211214", "211232", "233111",
)

START_B = 104
STOP = 106
# Stop-mönstret avslutas alltid med en 2 moduler bred bar.
STOP_FINAL_BAR = 2

MIN_ASCII = 32
MAX_ASCII = 126


def validate_code128_b(text: str) -> str:
    """Kontrollerar att texten kan kodas i Code 128-B (ASCII 32–126)."""
    cleaned = (text or "").strip()
    if not cleaned:
        raise ValueError("Streckkodstexten är tom.")
    for char in cleaned:
        if not MIN_ASCII <= ord(char) <= MAX_ASCII:
            raise ValueError(
                f"Tecknet {char!r} kan inte kodas i Code 128-B "
                f"(endast ASCII {MIN_ASCII}–{MAX_ASCII})."
            )
    return cleaned


def code128_b_values(text: str) -> List[int]:
    """Returnerar symbolvärdena för datatecknen (utan start/checksum/stop)."""
    cleaned = validate_code128_b(text)
    return [ord(char) - MIN_ASCII for char in cleaned]


def code128_b_check_value(text: str) -> int:
    """Beräknar checksum-symbolen (mod 103) för Code 128-B."""
    total = START_B
    for position, value in enumerate(code128_b_values(text), start=1):
        total += position * value
    return total % 103


def code128_b_symbols(text: str) -> List[int]:
    """Full symbolsekvens: [Start B] + data + [checksum] + [Stop]."""
    values = code128_b_values(text)
    symbols = [START_B] + values + [code128_b_check_value(text), STOP]
    return symbols


def code128_b_modules(text: str) -> str:
    """Returnerar hela streckkoden som binär sträng ('1' = bar).

    Inkluderar start, data, checksumma, stop och stoppens slutbara.
    Antal moduler = 11 * (n + 3) + 2.
    """
    bits: List[str] = []
    for symbol in code128_b_symbols(text):
        bits.append(_pattern_to_bits(CODE128_PATTERNS[symbol]))
    bits.append("1" * STOP_FINAL_BAR)
    return "".join(bits)


def code128_b_runs(text: str) -> List[int]:
    """Returnerar run-längder (bar/space växlande, börjar med bar)."""
    modules = code128_b_modules(text)
    runs: List[int] = []
    current = modules[0]
    count = 0
    for bit in modules:
        if bit == current:
            count += 1
        else:
            runs.append(count)
            current = bit
            count = 1
    runs.append(count)
    return runs


def module_count(text: str) -> int:
    """Totalt antal moduler (inklusive stoppens slutbara)."""
    return len(code128_b_modules(text))


def _pattern_to_bits(pattern: str) -> str:
    """'212222' → '11011001100' (bar/space-runlängder till binärt)."""
    bits: List[str] = []
    for index, width_char in enumerate(pattern):
        width = int(width_char)
        bits.append(("1" if index % 2 == 0 else "0") * width)
    return "".join(bits)


def draw_code128(
    canvas: object,
    x: float,
    y: float,
    width: float,
    height: float,
    text: str,
    show_text: bool = False,
    text_size: float = 6.0,
) -> bool:
    """Ritar en Code 128-B streckkod på en reportlab-canvas.

    Streckkoden fyller hela bredden `width` (quiet zone lämnas utanför —
    se till att minst 10 moduler finns som marginal runtom). Om
    `show_text` är True ritas texten i liten stil under strecken.

    Returnerar True om strecken ritades, False vid ogiltig text.
    """
    try:
        runs = code128_b_runs(text)
    except ValueError as exc:
        print(f"[Streckkod] {exc}")
        return False

    total_modules = sum(runs)
    module_width = width / total_modules

    canvas.saveState()
    canvas.setFillColor(colors.black)
    canvas.setStrokeColor(colors.black)

    bar_height = height if not show_text else height * 0.8
    position = 0.0
    for index, run in enumerate(runs):
        run_width = run * module_width
        if index % 2 == 0:  # jämna index är barer
            canvas.rect(x + position, y, run_width, bar_height, stroke=0, fill=1)
        position += run_width

    if show_text:
        from reportlab.pdfbase.pdfmetrics import stringWidth

        font = "Helvetica"
        text_width = stringWidth(text, font, text_size)
        canvas.setFont(font, text_size)
        canvas.drawString(x + (width - text_width) / 2.0, y, text)

    canvas.restoreState()
    return True


__all__ = [
    "CODE128_PATTERNS",
    "START_B",
    "STOP",
    "validate_code128_b",
    "code128_b_values",
    "code128_b_check_value",
    "code128_b_symbols",
    "code128_b_modules",
    "code128_b_runs",
    "module_count",
    "draw_code128",
]
