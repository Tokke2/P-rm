# PDFSORTER — Förslagslista

Denna fil driver **10-meddelanderegeln** (se `AGENTS.md`): efter var 10:e
chattmeddelande läggs en ny batch med **10 helt nya förslag** — aldrig
återbrukade. Gamla batcher arkiveras längst ner och används aldrig igen.

> **Städad 2026-11-25:** de gamla v1.0.0-raderna är borttagna. Filen började
> om ren (filen fanns inte i detta repo tidigare).

**Räknare:** batch #1 visad 2026-11-25 — nästa batch (10 helt nya förslag,
ej återbrukade) visas efter 10 chattmeddelanden därefter.

---

## Aktiv batch — #1 (2026-11-25) · 10 nya förslag

| # | Förslag | Beskrivning | Status |
|---|---------|-------------|--------|
| 1 | Filjämförande uppdaterare (REQ-K4) | Uppdateraren jämför filnamn + hash mot senaste Latest-release och uppdaterar endast det som skiljer. Backup tas bort först när uppdateringen verifierats. | Ny |
| 2 | Auto-rensning av loggar | Arkiverade loggar rensas automatiskt efter 7 dagar vid start. | Ny |
| 3 | Profilhanterare i Inställningar | Egen underflik där man skapar, byter och tar bort profiler (sparade förinställningar per kund/avdelning). | Ny |
| 4 | WYSIWYG-förhandsvisning | Ett live-preview av etiketten/verifikatet innan PDF skapas — ser ut precis som utskriften. | Ny |
| 5 | Batch-import från CSV/Excel | Importera hela etikettlistor från CSV/XLSX med kolumnmappning och felkontroll. | Ny |
| 6 | QR-kod på verifikatetiketter | Valfri QR-kod som länkar till journal/mapp/ärendenummer, renderad i vektor-PDF. | Ny |
| 7 | Hög-DPI-läge med skalbar UI | Skarp text och logotyp på alla skärmar (4K/skalning), fönstret startar i max höjd-läge med anpassad bredd och minimal scroll. | Ny |
| 8 | Mörkt/ljust tema | Temaväljare med hög kontrast för utskriftsmiljöer med svagt ljus; följer systeminställning. | Ny |
| 9 | Utskriftsarkiv med sökning | Historik over skapade PDF:er med sökning, återskapande och statistik per månad. | Ny |
| 10 | Energisnål läge | Lazy-rendering och paus av förhandsjobb vid batteridrift; lägre minnesanvändning vid stora listor. | Ny |

---

## Arkiverade batcher

*(inga ännu — fylls på när 10-meddelanderegeln triggas; arkiverade förslag
återbrukas aldrig.)*
