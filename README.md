# Pärmetikett Generator

Ett litet Tkinter-program som skriver utskriftsklara PDF-etiketter för pärmar
och arkivering: ryggetiketter (41×64 mm / 57×64 mm), indexetiketter och
verifikatetiketter för ett helt år.

## Nya förbättringar

### v1.1.0 — nya funktioner (förslag från 25-listan)

* **Checkruta per etikettrad** — kryssa för exakt vilka rader som ska
  skrivas ut eller ingå i arkivindex.
* **Smart arkivindex (#1)** — knappen _Skapa arkivindex_ genererar ett
  A4-ark med alla ikryssade etiketter och platskoder A1-01, A1-02 …
* **Streckkod Code 128-B (#2)** — valfri streckkod i etikettens underkant
  (kodad från etikettens första rad; verifikat kodar period + nummer + år).
* **Kvartal & halvår (#10)** — verifikat kan nu skapas per månad, kvartal
  (Q1–Q4) eller halvår (H1–H2).
* **Flerspråkiga etiketter (#11)** — månadsförkortningar på svenska,
  engelska eller norska (se/en/no).
* **Automatisk logotypkontrast (#16)** — mörka logotyper får automatiskt
  en vit baksida så de förblir tydliga på etiketten.
* **Förstärkta hörnmarkeringar (#22)** — L-formade markeringar i varje
  etiketthörn för exakt trimning.
* Nya inställningar (sparas som vanligt i `settings.json`):
  `verifikat_period`, `verifikat_language`, `barcode_labels`,
  `corner_marks`, `logo_contrast`.

### Tidigare

* **Logotyper i PDF, SVG, EPS och AI** — förutom PNG/JPG/TIFF m.fl.
  PDF-logotyper använder första sidan. Vektorer renderas i hög upplösning,
  tomma marginaler beskärs och logotypen centreras automatiskt på etiketten.
  Konvertering sker med det som finns installerat:
  * PDF: PyMuPDF → Ghostscript → Inkscape → pdftoppm
  * SVG: Inkscape → cairosvg → PyMuPDF
  * EPS/AI: Ghostscript → Inkscape
  Saknas alla converterare visas ett tydligt felmeddelande i stället för en
  tom etikett. Status syns på Hjälp-fliken.
* **Verifikat för hela året, uppdelat i 1 och 2 per månad** — knappen
  _Skapa BÅDA (1 & 2 per månad)_ skapar båda varianterna i ett svep:
  * `verifikat_2026_1_per_manad.pdf` — 12 lappar
  * `verifikat_2026_2_per_manad.pdf` — 24 lappar
  Ordningen är alltid JAN 1, JAN 2, FEB 1, FEB 2, … DEC.
  Det går fortfarande att välja 3–12 lappar per månad med den andra knappen.
* **Inställningar sparas** i `settings.json` (år, antal per månad, etikettyp,
  textstorlek, klipplinjer, logotyp, fönsterstorlek m.m.).
* **Robustare PDF-generering** — korrekt typsnittsfallback, bättre
  radbrytning av långa ord, sidbrytning som aldrig ritar utanför arket och
  ett enda ställe för all logotyphantering (`Script/logotyp.py`).

## Installation

Python 3.9+ (projektet är utvecklat för 3.12):

```bash
python -m pip install -r requirements.txt
python folder.py
```

`requirements.txt` innehåller bara det nödvändiga (reportlab, Pillow,
ttkthemes). För vektorlogotyper räcker det med **en** av converterarna:

```bash
python -m pip install pymupdf        # PDF + SVG, rekommenderas
python -m pip install cairosvg       # SVG (behöver libcairo)
# eller installera Ghostscript, Inkscape / poppler på systemnivå
```

## Användning

1. Välj etikettyp (Smal, Tjock eller Index).
2. Klicka **Välj logotyp** och välj en PDF-, SVG-, EPS-, AI- eller bildfil.
   Filen kan också läggas i mappen `Logotyp/` och väljas därifrån.
3. Fyll i etiketttexterna till höger (Ctrl+N lägger till ett fält).
4. Klicka **SKAPA PDF**. Filen hamnar i `export/` och öppnas automatiskt.
5. För verifikat: välj år och klicka **Skapa BÅDA (1 & 2 per månad)**.
   Båda PDF:erna hamnar i `export/`.

Klipplinjer, textstorlek, autoanpassning och logotypens avstånd från toppen
kan justeras i vänsterpanelen. Allt sparas tills nästa gång appen startar.

## Tester

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Testerna är huvudsakligen huvudlösa (de behöver inte Tk): de kontrollerar
verifikatordning och filnamn, PDF-ritning samt import av PDF-/SVG-/PNG-logotyp.

## Filstruktur

| Fil | Ansvar |
| --- | --- |
| `folder.py` | Huvud-GUI och PDF-skapande |
| `Script/label.py` | Ritlogik för etiketter + typsnitt |
| `Script/logotyp.py` | Logotypimport och konvertering (PDF/SVG/EPS/raster) |
| `Script/verifikat.py` | Ren logik för verifikattexter och filnamn |
| `Script/settings_store.py` | Läs/skriv `settings.json` |
| `spec.md` | Utförlig teknisk specifikation |

© Copyright Rickard Längkvist — All rights reserved.
