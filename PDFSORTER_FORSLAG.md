# PDFSORTER — Förslagslista

Denna fil driver **10-meddelanderegeln** (se `AGENTS.md`): efter var 10:e
chattmeddelande läggs en ny batch med **10 helt nya förslag** — aldrig
återbrukade. Gamla batcher arkiveras längst ner och används aldrig igen.

> **Städad 2026-11-25:** de gamla v1.0.0-raderna är borttagna. Filen började
> om ren (filen fanns inte i detta repo tidigare).

**Räknare:** batch #1 visad 2026-11-25 — nästa batch (10 helt nya förslag,
ej återbrukade) visas efter 10 chattmeddelanden därefter. Båda listtyperna
(10-batchen och 25-förslagslistan) ska alltid även **skrivas i chatten**
(AGENTS.md §6).

---

## Arkiverad batch — "25 förslag" (2026-11-25 · skriven i chatten)

25 nya förslag som konkurrenterna saknar och användare efterfrågar —
**inget** av dessa får återbrukas i framtida listor:

1. Smart arkivindex — auto-genererat A4-indexark med alla pärmar + platskoder
2. Streckkoder (Code 128/EAN) på ryggetiketter för scannersökning
3. Färgkodning per kund/avdelning — färgband/rand i etikettens kant
4. Hyllplatsfält med auto-numrering (A1-01, A1-02 …) för pärmserier
5. Serier/dubbletter i ett svep — "12 identiska pärmar" med löpnummer
6. Årsringsbibliotek — "kopiera förra årets etikettuppsättning"
7. Validering av verifikatnummer — varnar för dubletter/gap i serien
8. Bevarandetidsfält ("Arkiveras till 2031", GDPR/bokföringslag)
9. Skrivarkalibrering — sparade marginaler per skrivare, träffar rutmönstret exakt
10. Kvartals-/halvårsgenerator (Q1–Q4, H1–H2) utöver månader
11. Flerspråkiga etiketter (sv/en/no) med en växel
12. Mall-läge med skrivskydd — lås layout, låt bara texter ändras
13. Foto/scanna pärmrygg → OCR-förslag på ny etikett
14. "Hitta rätt pärm" — skriv verifikatnummer, se pärm + månadslapp
15. Indexflikar i färg för snabb bläddring i pärmryggen
16. Automatisk logotypkontrast (ljus/mörk text efter bakgrund, WCAG)
17. Inbyggd mm-skala att skriva ut och mäta pärmryggens bredd med
18. Batch-ID i sidfot — spårbarhet: vilken dator/körning som skrev ut
19. PDF/A-arkivering av etikettfilerna (långtidsbevarande-krav)
20. Signaturrad på verifikatet — "utskrivet av / granskat av" + datum
21. Kontrollfält: antal lappar per pärm kontrolleras mot arkivplanen
22. Klipplinjer med förstärkta hörnmarkeringar för exakt trimning
23. Skyddsläge — skrivskydda inställningar med PIN (standardiserade kontor)
24. Snabbknappar för topp-3-konfigurationer (enklicksutskrift)
25. Övervakad mapp — CSV/JSON i mappen → PDF skapas automatiskt

---

## Aktiv batch — #1 (2026-11-25) · 10 nya förslag

**Statusuppdatering 2026-11-25 (v1.1.0):** användaren valde att bygga
25-listans nr 1, 2, 10, 11, 16, 22 + en checkruta per rad. De är nu
**byggda och testade** — se statuskolumnen nedan (arkiverade listans
förslag #1–#25). Inga av dem får återbrukas i nya listor.

| # | Förslag | Beskrivning | Status |
|---|---------|-------------|--------|
| 1 | Filjämförande uppdaterare (REQ-K4) | Uppdateraren jämför filnamn + hash mot senaste Latest-release och uppdaterar endast det som skiljer. Backup tas bort först när uppdateringen verifierats. | Ny |
| 2 | Auto-rensning av loggar | Arkiverade loggar rensas automatiskt efter 7 dagar vid start. | Ny |
| 3 | Profilhanterare i Inställningar | Egen underflik där man skapar, byter och tar bort profiler (sparade förinställningar per kund/avdelning). Endast appar som använder profiler. | Ny |
| 4 | WYSIWYG-förhandsvisning | Ett live-preview av etiketten/verifikatet innan PDF skapas — ser ut precis som utskriften. | Ny |
| 5 | Batch-import från CSV/Excel | Importera hela etikettlistor från CSV/XLSX med kolumnmappning och felkontroll. | Ny |
| 6 | QR-kod på verifikatetiketter | Valfri QR-kod som länkar till journal/mapp/ärendenummer, renderad i vektor-PDF. | Ny |
| 7 | Hög-DPI-läge med skalbar UI | Skarp text och logotyp på alla skärmar (4K/skalning), fönstret startar i max höjd-läge med anpassad bredd och minimal scroll. | Ny |
| 8 | Mörkt/ljust tema | Temaväljare med hög kontrast för utskriftsmiljöer med svagt ljus; följer systeminställning. | Ny |
| 9 | Utskriftsarkiv med sökning | Historik over skapade PDF:er med sökning, återskapande och statistik per månad. | Ny |
| 10 | Energisnål läge | Lazy-rendering och paus av förhandsjobb vid batteridrift; lägre minnesanvändning vid stora listor. | Ny |

---

## Byggda förslag — 25-listan (2026-11-25 · skriven i chatten)

Från "25 förslag som konkurrenterna saknar" (arkiverad nedan) byggdes
följande i **v1.1.0**, plus en **checkruta per etikettrad** (välj vad som
ska skrivas ut):

| Nr i 25-listan | Funktion | Implementering |
|----------------|----------|----------------|
| 1 | Smart arkivindex | `Script/arkivindex.py` — A4-indexark med platskoder A1-01… + knapp i GUI:t |
| 2 | Streckkoder | `Script/streckkod.py` — Code 128-B (ISO 15417, verifierad tabell) i etikettens underkant |
| 10 | Kvartal/halvår | `verifikat.py` periodlägen: manad/kvartal (Q1–Q4)/halvar (H1–H2) + GUI-val |
| 11 | Flerspråkiga etiketter | månadsförkortningar se/en/no i verifikat + GUI-val |
| 16 | Automatisk logotypkontrast | `logotyp.estimate_luminance()` + vit baksida bakom mörka logotyper |
| 22 | Förstärkta hörnmarkeringar | `label.corner_mark_lines()` — L-formade hörnmarkeringar per etikett |
| — | Checkruta per rad | `folder.py`: kryssa per etikettrad → styr utskrift + arkivindex |

---

## Arkiverade batcher

*(inga ännu — fylls på när 10-meddelanderegeln triggas; arkiverade förslag
återbrukas aldrig.)*
