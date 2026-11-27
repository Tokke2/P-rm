# Pärmetikett Generator

En gratis, reklamfri Qt6-app (PySide6) som skriver utskriftsklara
PDF-etiketter för pärmar och arkivering: ryggetiketter (41×64 mm /
57×64 mm), indexetiketter och verifikatetiketter för ett helt år.

## Nya förbättringar

### v1.10.1 — logotypfix: PyMuPDF ingår — Inkscape är aldrig ett krav

* **Beroende (§4): `PyMuPDF>=1.24` tillagd i requirements.txt** — den
  inbyggda logotypmotorn. SVG/PDF-logotyper fungerar nu efter en enkel
  `pip install -r requirements.txt`, **utan Inkscape, Ghostscript eller
  andra externa verktyg** (Inkscape är aldrig ett krav — bara valfri
  fallback tillsammans med cairosvg/poppler).
* SVG-kedjan är nu **PyMuPDF → cairosvg → Inkscape** (PyMuPDF först;
  var verifierad offline med riktig SVG-rendering: synliga pixlar +
  logotypen syns i genererad PDF även med fyll-läget).
* **Ritfel syns nu på Loggar-fliken** (kod LOGO_DRAW) istället för tysta
  konsolutskrifter — en logotyp som inte kan ritas kan aldrig försvinna
  utan spår.
* Hjälp-fliken visar nu **"Logotypmotor: PyMuPDF ✓ (ingår — inga externa
  verktyg krävs; Inkscape är aldrig ett krav)"** (eller tydlig instruktion
  om PyMuPDF saknas).
* **Viktigt för updaterade installationer:** updateraren kopierar filer
  men installerar inte Python-paket — kör en gång:
  `python -m pip install -r requirements.txt`
* Tester: 6 nya (inkl. två riktiga SVG→PNG→PDF-renderingstester) —
  **167 st totalt**.

### v1.10.0 — Tjock rygg som standard + Inställningar-flik + text fyller alltid etiketten

* **Tjock rygg är standard** (57×64 mm) — Smal/Index väljs som vanligt;
  ändras bara för nya installationer (din sparade inställning vinner).
* **Ny Inställningar-flik** (Generator | **Inställningar** | Hjälp | Loggar)
  — här ställs allt in, i två kort: **Etiketter & utskrift** (Flera
  etiketter, Klipplinjer, Hörnmarkeringar, Streckkod, Logotypkontrast,
  Antal) och **App & system** (Auto-uppdatering 00:00 + Sök uppdatering,
  Autostart, Tray vid stängning, PDF per rad). Vänsterpanelen i Generator
  är nu ren: bara Etikettyp, Logotyp och åtgärder.
* **Texten fyller alltid etiketten (5 px marginal) — delas aldrig upp**:
  * Nytt fyll-läge i etikettritningen: texten är alltid **EN rad** som
    automatiskt **växer eller krymper** tills den fyller etiketten med
    **5 px marginal** från kanterna (bredd + höjd beaktas; logotypens
    utrymme respekteras)
  * Radbrytningen är helt avstängd i fyll-läget — långa texter krymper i
    stället (vakttest anropar aldrig radbrytaren)
  * "Textstorlek" + "Autoanpassa text"-kryssrutan är borttagna (verkar
    alltid) — gamla settings-nycklar sparas oförändrade för kompatibilitet
  * Gäller rygg-etiketter, index-etiketter och verifikatetiketter
* Tester: 11 nya (fill-matematik 6 + flik/standard 5) — **161 st totalt**

### v1.9.0 — ny design: snyggare, enklare, proffsigare, modernare

* **Modern QSS design-system** (brandfärgerna bevarade: djupblå + orange):
  * **Kort-look**: varje grupp (Etikettyp, Logotyp, Inställningar,
    Verifikat) är ett vitt kort med mjuk kant + rundade hörn
  * **Platta "understryknings"-flikar** — aktiv flik markeras med orange
    underkant istället för tyng 3D-panel
  * **Tysta sekundära knappar** (vit + kant, hover-blå nyans) så att den
    fyllda orange accentknappen (SKAPA PDF) verkligen sticker ut
  * **Mjuka tillstånd**: hover, pressed, disabled, fokus-orange ring på
    inmatningar, stilrena menyer, mörk tooltip, smala (8px) scrollbars
  * Kryssrutor/radioknappar med rundade indikatorer i accentfärg;
    Loggar-tabellen med ränder + ljus headerrad
* **Enklare UI** — samma funktioner, mindre brus:
  * Utvecklar-suffix borttagna från alla synliga texter: inte längre
    "(#1)"/"(#22)"/"(#16)"/"(REQ-K4)" i knappar/rutor/menyer (vakttest
    ser till att de aldrig kommer tillbaka)
  * "Antal etiketter" är nu en horisontell rad; ren fönstertitel
    ("Pärmetikett Generator" utan årtal)
  * Appens logotyp är nu även **ikon i aktivitetsfältet** (taskbar)
* Språkbytet (sv/en) fungerar som vanligt live — alla nya texter är
  översatta; mushjul, tray, autostart osv. oförändrade
* Tester: 5 nya design-vakttester — **150 st totalt**

### v1.8.1 — P0-buggfix språkbyte + updateraren städar inaktiva filer

* **Kraschfix (språk/GUI)**: `apply_language` kallade `text()` på
  QGroupBox — men QGroupBox har `title()`/`setTitle()` (v1.8.0-
  regression). Nu separerad gren; "Inställningar" är också översättnings-
  klar. Vakttest ser till att grenen förblir separerad.
* **Updateraren städar INAKTIVA filer** (användarönskemål): efter varje
  lyckad uppdatering rensas
  * `__pycache__`-mappar + `*.pyc`/`*.pyo` (bytecode)
  * överblivna `*.tmp` (t.ex. halvskriven settings.json.tmp)
  * **tomma mappar** (när en mapp blivit tom efter att dess filer
    raderats som utgångna)
  * Användardata skyddas alltid: `Loggar/`, `Logotyp/`, `Profiler/`,
    `export/`, `Uppdatering_backup/` röras aldrig.
  * Antal städade poster rapporteras i JSON-bootstrap (`"städade": N`)
    och i apploggen.
* Tester: 7 nya (städning 5 + språk-vakt 2) — 145 st totalt.
* Uppdatera: `python Script/updater.py` (v1.8.1 städar samtidigt som den
  uppdaterar).

### v1.8.0 — tray, skriv ut direkt, språk sv/en, mushjul, start utan terminal + 2 förslag

* **Systemfältsikon (tray) (#1)**: ikon i systemfältet med snabbmeny (visa,
  sök uppdatering, auto-upd-på/av, Stöd-menyn, Avsluta). Ny kryssruta
  **"📁 Minimera till systemfältet (tray) vid stängning"** — stäng = körs
  kvar i tray (notis första gången). **Tray-notis** när auto-uppdatering
  00:00 installerat något.
* **🖨 Skriv ut direkt (#2)**: ny knapp bredvid SKAPA PDF — skickar PDF:n
  direkt till standardskrivaren (Windows print-verb); PDF:en sparas som
  vanligt i Export-mappen.
* **📄 Skapa även separata PDF:er per rad (#5)**: kryssruta — utöver den
  samlade PDF:en skapas en egen fil per etikettrad (bra när flera personer
  ska dela upp utskriften).
* **GUI-språk sv/en (#7)**: menyn **Hjälp & Stöd → 🌍 Språk / Language** —
  hela gränssnittet (flikar, menyer, knappar, rutor, tabellrubriker) +
  fullständig hjälptext översätts **live, utan omstart**. Sparas i
  settings (`gui_language`).
* **Mushjul på omarkerade rullgardiner** (användarönskemål): Qt6 vägrar
  wheelevents på widget utan fokus — nu lyssnar alla rullgardiner
  (period/språk) och spinboxar (år/lappar/antal/storlek/toppx) på mushjulet
  direkt vid hovring, utan att klicka först.
* **Start utan terminal (§9)**: **`Starta_Parmetikett.vbs`** i
  programmappen — dubbelklicka, appen startar med pythonw (inget fönster).
  Nytt menyval **"📎 Skapa skrivbordsgenväg (utan terminal)"** skapar en
  .lnk på skrivbordet (pythonw, ikon, rätt arbetskatalog). Autostart-valet
  (🚀 checkbox/meny) finns kvar som tidigare.
* **Settings-självdiagnos (#9)**: settings.json kontrolleras vid start —
  korrupt fil **repareras automatiskt från intern backup**
  (settings.json.bak, uppdaterad vid varje sparning); sparningen är nu
  atomisk (ingen halvskriven fil). Loggas på Loggar-fliken.
* Nya settings-nycklar (§4): `minimize_to_tray`, `separate_row_pdfs`,
  `gui_language` — alla med svenska-standardvärden, inga gamla nycklar
  borttagna.
* Tester: 15 nya (settings-diagnos 6 + vakttester 9) — **138 st totalt**.

### v1.7.4 — förslagsbatch #2 (10-meddelanderegeln)

* Uppdaterarens JSON-bootstrap bekräftad live av användaren (ok/verified,
  5 filer, backup borttagen vid verifiering).
* PDFSORTER_FORSLAG.md: batch #1 arkiverad, **batch #2 visad** (10 nya,
  icke-återbrukade förslag i Qt-eran: tray-ikon, skriv ut direkt,
  headless-CLI, dra-och-släpp-rader, samlad serie-PDF, filnamnsmall,
  GUI-språk, "Vad är nytt", settings-självdiagnos, dela-fil).
* Ingen kodändring i GUI/moduler — dokument-/ledger-uppdatering.

### v1.7.3 — P0-buggfix: QUrl importerad från fel Qt-modul

* **Kraschfix**: `QUrl` bor i **QtCore** (inte QtGui) — `cannot import
  name 'QUrl' from 'PySide6.QtGui'` på Windows. Importen flyttad:
  `QtCore(QUrl, QTimer, Qt)` + `QtGui(QAction, QDesktopServices, QFont, QIcon)`.
* **Ny vakt mot fel modulplacering**: testet validerar VARJE PySide6-
  import i folder.py mot **PySide6:s .pyi-stubbar** (den officiella
  modulplaceringen — textfiler, fungerar även där grafikbiblioteket
  saknas). Negativt verifierad: hittar fel som denna.
* Tester: 123 st totalt.
* Uppdatera en installation som inte startar: `python Script/updater.py`

### v1.7.2 — P0-buggfix: NameError QAction vid menybygget (v1.7.0-regression)

* **Kraschfix**: menyerna kallade `QAction`/`QMenu`/`QDesktopServices`/
  `QUrl` — men import-raderna kom aldrig in i folder.py (v1.7.0-
  regression; redigeringen rapporterade framgång men applicerades inte).
  Nu importerade korrekt från `PySide6.QtGui` respektive `PySide6.QtWidgets`.
* **Ny vaktklass som hade fångat detta i sandbox**: AST-audit kontrollerar
  att VARJE Qt-namn som används också importeras (körs alltid, kräver
  inget grafikbibliotek) + pyflakes-vakt mot alla undefined names (när
  pyflakes finns). pyflakes kördes även manuellt — noll undefined names.
* Kosmetisk fix: onödig `Dict[str, List[str]]`-annotation i test_updater.
* Tester: 3 nya — 122 st totalt.
* Uppdatera en installation som inte startar: `python Script/updater.py`

### v1.7.1 — P0-buggfix: autostart kraschade appstarten på Windows

* **Kraschfix (winreg-API)**: autostart kallade `key.QueryValueEx(...)` —
  men `winreg.PyHKEY`-objektet har bara `Close`/`Detach`;
  `SetValueEx`/`QueryValueEx`/`DeleteValue` finns på **modulnivå** med
  nyckeln som första argument. Kraschen inträffade vid appstart när
  autostart-checkboxen initierades (v1.7.0-regression).
* **Försvarslag**: alla winreg-anrop är nu insvepta så att en udda
  registery-implementation aldrig kan krascha appstarten — autostart
  blir bara no-op med fellogg.
* Permanent regressionstest med exakt riktig winreg-API-simulering
  (3 nya tester) — 119 st totalt.
* Uppdatera en installation som inte startar: `python Script/updater.py`

### v1.7.0 — menyer (Uppdatera + Hjälp & Stöd) + stöd-meny à la TaskBord

* **Ny menybar**:
  * **Uppdatera**: "⬇️ Sök uppdatering nu (REQ-K4)", "🕒 Auto-uppdatering
    00:00 varje dag" (av/på — synkad med checkboxen), "📂 Öppna Export-mappen"
  * **Hjälp & Stöd**: "🚀 Autostart vid inloggning" (av/på — synkad),
    **💖 Stöd Pärmetikett Generator…** → Donera via PayPal / Bjud på en
    kaffe via Ko-fi / ⭐ Ge en stjärna på GitHub, "🐞 Rapportera fel /
    förslag", "🌐 GitHub-projektet", "ℹ️ Om Pärmetikett Generator"
    (version + stödinfo)
* **Högerklick på fönstret** → 💖 Stöd … + uppdatering + Om
  (samma mönster som TaskBord)
* Donationslänkar öppnas i **standardwebbläsaren**; appen hanterar aldrig
  betalningsuppgifter
* **SUPPORT.md** tillagd (stöd/hjälp-dokument anpassad till appen) och
  länkad från README; Hjälp-fliken har en STÖD-sektion
* Tester: 8 nya vakttester för menyer/stöd — **116 st totalt**

### v1.6.0 — Qt är nu appen (tkinter ersatt)

* **`folder.py` är nu Qt6-appen** (PySide6) — tkinter-versionen är
  **ersatt**. Samma layout och alla funktioner som tidigare: flikarna
  Generator/Hjälp/Loggar, checkrutor per rad, streckkoder, arkivindex,
  verifikat (manad/kvartal/halvar × se/en/no), updater (REQ-K4) +
  auto-uppdatering 00:00 varje dag
* **Automatisk hög-DPI** (Qt6) → skarpast möjliga text på 4K/skalning (§11)
* **QSS-design i logotypens färger** (djupblå + orange), inbyggd
  sortering + kolumnflyttning i Loggar-tabellen (§10)
* **Autostart vid inloggning** med `pythonw.exe` — **utan terminal** (§9);
  skanning/konvertering körs med `CREATE_NO_WINDOW` (konsol blinkar aldrig)
* **`folder_qt.py`** är nu en kompatibel startare (gamla genvägar och
  autostart-poster pekar dit — de fortsätter fungera)
* **Beroenden (§4):** `requirements.txt` — PySide6 krävs nu,
  `ttkthemes` borttagen (tkinter-GUI:t finns inte längre). Inga andra
  ändringar; alla Script-moduler oförändrade.
* Kör: `python folder.py` (eller `pythonw folder.py` — utan terminal)
* Tester: 108 st, alla gröna

### v1.5.0 — Qt6-version med samma layout + autostart + helt utan terminal

* **Ny Qt6-version** (`folder_qt.py`, PySide6) — **exakt samma layout och
  funktioner** som tkinter-versionen (samma flikar Generator/Hjälp/Loggar,
  samma paneler och knappar), med:
  * **Automatisk hög-DPI-skärpa** (Qt6 skalar själv → skarpast möjliga
    text på 4K/skalning, §11)
  * **QSS-design i logotypens färger** (djupblå #1E3A5F + orange #F6A03C)
  * Loggar-tabellen har **inbyggd sortering (klick) och kolumnflyttning
    (dra)** — ännu smidigare än tkinter-versionen (§10)
  * Samma updater (REQ-K4) + **auto-uppdatering 00:00** + tyst startkontroll
  * Startar i max höjd-läge med anpassad bredd (`availableGeometry` =
    skärm minus taskbar, §11)
* **Autostart vid inloggning** (ny checkbox): skapar Windows
  autostart-post med **pythonw.exe** → appen startar automatiskt vid
  inloggning **utan terminal** (`Script/autostart.py`, HKCU Run-nyckel)
* **Helt utan terminal (§9)**:
  * `pythonw.exe` används av autostart (ingen konsol vid start)
  * **Skanning/konvertering** (PyMuPDF/Ghostscript/Inkscape) körs nu med
    `CREATE_NO_WINDOW` på Windows — konsolfönstret **blinkar aldrig**
  * pythonw-skydd: `sys.stdout/stderr` omdirigeras om de saknas (print
    kraschar inte längre vid terminalfri start) — i båda versionerna
* **Kör Qt-versionen:** `python folder_qt.py` (kräver `pip install
  PySide6` — nytt beroende i requirements.txt). Tkinter-versionen
  (`folder.py`) finns kvar som fallback utan beroenden.
* Tester: 20 nya (autostart med fake-registret, no-console, statisk
  Qt- struktur-audit) — **105 st totalt**

### v1.4.1 — P0-buggfix: appen startade inte på Windows

* **Kraschfix (ttk-options)**: `ttk.Combobox` fick felaktigt `command=`
  (ttk har ingen sådan option — kraschade med `unknown option "-command"`
  vid start på Windows/Python 3.15). Period- och språk-väljarna binder nu
  `<<ComboboxSelected>>` i stället.
* **Dold krasch fixad i samma svep**: `ttk.Checkbutton(width=2)` (bredd är
  inte en ttk.Checkbutton-option) — borttagen.
* **Statisk vaktest** (`tests/test_gui_statik.py`): AST-skanning av
  folder.py som förbjuder ogiltiga ttk-options för alltid (körs även utan
  tkinter/display).
* **Bootstrap-uppdatering**: `python Script/updater.py` kör updateraren
  **utan GUI** — används om appen inte kan starta (exakt detta läge):
  den jämför filer mot Latest-releasen och lagar installationen.

### v1.4.0 — auto-uppdatering 00:00 varje dag (REQ-K4)

* **Auto-uppdatering varje midnatt**: appen kör REQ-K4-uppdateringen
  automatiskt kl **00:00** om en nyare Latest-release finns — helt tyst,
  inga dialoger på natten, allting loggas i apploggen/felloggen
* **Uppecatchning**: startar du appen inom 5 minuter efter 00:00 utförs
  den missade körningen direkt
* Av/på via checkboxen **"🕒 Auto-uppdatering 00:00 varje dag"** i
  vänsterpanelen (standard: **på**), sparas i settings.json
  (`auto_update_daily`)
* Samma säkerhet som manuell uppdatering: filjämförelse (sha256), backup
  tas bort först vid verifierad uppdatering, rollback vid fel, main-releaser
  vägras
* Serialiseringslås — auto- och manuell uppdatering kan aldrig köras
  samtidigt

### v1.3.0 — uppdaterare i appen (REQ-K4, §3)

* **Ny knapp "⬇️ Sök uppdatering (REQ-K4)"** i vänsterpanelen:
  1. Hämtar senaste **Latest**-release från GitHub (api.github.com)
  2. **Vägrar releaser som pekar på `main`** (§1 — jobba aldrig emot main)
  3. **Jämför filer** (relativ sökväg + sha256) mot release-källarkivet
     (codeload.github.com) — **uppdaterar endast det som skiljer**
  4. **Backar upp** varje fil som ändras/raderas till `Uppdatering_backup/`
  5. Verifierar efteråt: filuppsättning + hash ska **exakt** matcha releasen
  6. **Backup tas bort först när verifieringen lyckats** — vid fel: full rollback
* **Tyst kontroll vid appstart** (bakgrundstråd): loggar i apploggen om en
  ny release finns — nedladdning sker först när användaren klickar
* Användardata (`settings.json`, `Loggar/`, `Logotyp/`, `Profiler/`,
  `export/`) röras **aldrig** av uppdateraren
* Allt loggas i Loggar-fliken (UPD_CHECK/UPD_DOWNLOAD/UPD_APPLY/UPD_VERIFY)
* Ny fil `VERSION.txt` (installerad version) — uppdateras av updateraren
* Inga externa beroenden: standardbibliotek (`urllib`, `tarfile`, `hashlib`)
* Kör i bakgrundstråd — GUI:t fryser inte (§9: inget terminalfönster)

### v1.2.0 — loggsystem (§8) + skärm/DPI-paket (§11)

* **Komplett loggsystem** — ny flik **Loggar**:
  * **Fellogg** visar alla **aktiva fel** — när ett fel åtgärdats (t.ex.
    lyckad logotypinläsning) försvinner det **automatiskt**; fel kan också
    **rensas manuellt** (valda eller alla)
  * **Applogg** sparar händelser: skapade PDF:er, valda logotyper, städning
  * **Gårdagens loggposter arkiveras** till `Loggar/arkiv/`, och arkiverade
    loggar **raderas automatiskt efter 7 dagar** (vid varje appstart)
  * Felloggens kolumner kan **sorteras** (klick på kolumnhuvud) och
    **flyttas** (dra huvudet) enligt §10
* **Skärm & skärpa (§11)**:
  * **DPI-medveten** start på Windows (`SetProcessDpiAwarenessContext`) —
    skarp text på 4K/hög skärmskalning, ingen grumlig rendering
  * Fönstret startar i **max höjd-läge** anpassat efter skärmen (minus
    taskbar) med **anpassad bredd** (sparad bredd minns), centrerad
  * Tydligare typsnitt (Segoe UI + skalning efter DPI)
* **Appens logotyp som vektor för tryck** — `assets/app_logotyp.svg`
  (redigerbar) + kvadratisk PNG-ikon som används som **fönsterikon**; ny
  knapp **⭐ Använd appens logotyp** lägger den direkt på etiketterna
* **Buggfix (SVG)**: PyMuPDF-rendering av SVG öppnas nu via filsökväg —
  korrekt proportioner på kvadratiska SVG-logotyper (tidigare kunde
  sidhöjden bli fel via stream-öppning)
* Kör i Windows utan terminalfönster: starta med `pythonw.exe` (§9)

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

## Stöd Pärmetikett Generator

Appen är gratis och reklamfri — donationer är helt frivilliga och låser
inte upp några extra funktioner. Du hittar länkarna i appen via
**Högerklicka → 💖 Stöd Pärmetikett Generator…** eller menyn
**Hjälp & Stöd**:

| Tjänst | Länk |
| --- | --- |
| PayPal | [Donera via PayPal](https://paypal.me/Rickard3dPrint) |
| Ko-fi | [Bjud på en kaffe via Ko-fi](https://ko-fi.com/tokke2) |

Hjälp till utan att donera: ge [projektet en stjärna på GitHub](https://github.com/Tokke2/P-rm),
rapportera fel/förslag i [Issues](https://github.com/Tokke2/P-rm/issues)
eller dela projektet. Läs mer i [SUPPORT.md](SUPPORT.md).

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
