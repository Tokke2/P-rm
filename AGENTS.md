# AGENTS.md — Regler för Tokke2/P-rm (Pärmetikett Generator)

Den här filen är den **enda sanningskällan** för arbetsregler i repot.
Varje ny chatt/agent ska läsa den **först** och följa alla regler utan
undantag. Regler markerade **HÅRD** får aldrig brytas.

**Anpassning per app:** filen gäller appen *Pärmetikett Generator*
(`folder.py` + `Script/`). Regler märkta **[APP]** är anpassade för just
denna app; övriga regler är universella. Vid ny app kopieras filen till det
repots rot, universella regler behålls och **[APP]**-reglerna skrivs om efter
appens teknik (se §12).

---

## 1. Branch-reglerna (HÅRD)

* Repot ska alltid ha **exakt EN arbetsbranch**: den aktuella
  arena-branchen. Alla gamla session-brancher tas bort (det är gjort —
  `arena/813a1786-p-rm` raderad 2026-11-25).
* `main` står kvar som GitHub:s default-branch endast för att sandboxens
  token saknar admin-rättighet att byta/radera den. `main` är **förbjudet
  område**: aldrig committa, pusha eller merga emot den, och den ska
  aldrig återskapas eller uppdateras — **speciellt inte vid
  appuppdateringar**.
* **Aldrig merge** — inte `git merge`, inte `gh pr merge`, inga mergar i
  någon form. Ändringar committas alltid direkt på arbetsbranchen.
* Om gamla brancher dyker upp igen: ta bort dem så att endast **en** branch
  är kvar.

## 2. Release-regeln (HÅRD)

* Vid **varje kodförändring** ska GitHub-releasen alltid uppdateras **i samma
  veva som pushen**:
  1. Pusha koden till arbetsbranchen.
  2. Skapa/uppdatera release som innehåller **exakt** den pushade koden.
  3. Markera releasen som **Latest**.
* En release som inte speglar senaste koden är alltid ett **fel**.
* Versionshöjning: patch för buggfixar, minor för ny funktionalitet,
  major vid breaking change.
* **Driftnotis (sandlåda):** uppladdning till `uploads.github.com` är
  blockerad — använd därför releasens **auto-genererade källarkiv** (zipball/
  tarball, hämtas via `api.github.com`/`codeload.github.com`) som
  uppdaterarens jämförelsekälla. Kommandomönster:
  `gh release create vX.Y.Z --target <arbetsbranch> --latest --notes "…"`.
  Egen asset-uppladdning (`gh release upload`) fungerar inte i sandlådan.

## 3. REQ-K4 — filjämförelse i uppdateraren (HÅRD)

* Appens uppdaterare jämför **filer** (namn + innehåll/hash) mot den
  senaste **Latest**-markerade releasen och uppdaterar **endast det som
  skiljer** — aldrig halv-uppdaterat läge.
* Ingen release får markeras **Latest** utan att exakt spegla branchens kod.
* Uppdateringen ska vara säker: backup tas bort **först när** uppdateringen
  verifierats som lyckad.

## 4. Inga tysta beroende- eller gränssnittsbrott (HÅRD)

* Beroenden (`requirements.txt`, `requirements-dev.txt`) och interna
  gränssnitt (importer, funktions-/klasssignaturer, `settings.json`-nycklar)
  får **inte** ändras tyst.
* Varje sådan ändring ska nämnas **explicit** i commit-meddelande och i
  changeloggen (`spec.md` / `README.md`) — och vara bakåtkompatibel, eller
  tydligt märkt som breaking med motivering.

## 5. Testkrav innan klar (HÅRD)

* Inget arbete är "klart" förrän testerna passerar lokalt:
  `python -m unittest discover -s tests`
* Testerna körs **alltid** före push och release. Ny funktionalitet ska
  komma med tester när det är rimligt.

## 6. 10-meddelanderegeln (HÅRD)

* Efter var **10:e chattmeddelande** visas en **ny förslagslista med 10 helt
  nya förslag** — **aldrig återbrukade** från tidigare listor.
* Listorna förs i `PDFSORTER_FORSLAG.md`; gamla batcher arkiveras i filen
  och används aldrig igen.

## 7. Regel-insättning på GitHub (HÅRD — metaregel)

* Skriver användaren "**- hård regel**" eller "**regel**" i chatten ska den
  nya regeln **omedelbart** skrivas in i denna fil, pushas till
  arbetsbranchen och inkluderas i release-uppdateringen (§2) — i samma tur.

## 8. Loggning & felhantering (HÅRD — [APP])

* Appen ska ha **två kompletta loggar**: **applog** (all normal
  händelselogging) och **fellog**.
* **Felloggen innehåller alla aktiva fel.** När ett fel har blivit åtgärdat
  tas det **automatiskt bort** från felloggen.
* Användaren ska också kunna **rensa bort fel manuellt** ur loggen efter att
  de är åtgärdade.
* **Gårdagens loggar arkiveras** automatiskt, och **arkiverade loggar
  raderas efter 7 dagar**.

## 9. Terminalfönster (HÅRD — [APP])

* Inget terminal-/konsolfönster visas, **varken vid start eller skanning** —
  konsolen ska alltid startas **minimerat/dolt** (t.ex. `pythonw.exe` eller
  `CREATE_NO_WINDOW` på Windows).
* Själva appfönstret följer skärmreglerna i §11 (max höjd-läge, anpassad
  bredd).

## 10. Tabeller & kolumner (regel — [APP])

* Har appen tabeller/kolumner ska användaren kunna **sortera** kolumner
  (klick på kolumnhuvud) och **flytta** dem (dra-och-släpp) — med vald
  ordning ihåkommen mellan sessioner.

## 11. Stående kvalitetskrav ([APP] — alltid beakta)

* **Skärpa & skärm**: skarp rendering vid alla DPI/skärmstorlekar — ingen
  grumlig text/bild/kolumn; tydliga typsnitt; layout som anpassar sig till
  skärmen; fönstret startar i max höjd-läge (beroende på skärm) med anpassad
  bredd; allt synligt, minimal scroll.
* **Design**: bättre logotyp (skarp, används överallt; vektor/redigerbar för
  tryck) och nya bättre ikoner.
* **Prestanda**: bättre minneshantering, snabbare, energisnålare.
* **Inställningar**: egen underflik för att skapa profiler; ruttvalet från
  ttk-versionens projektskapare ska finnas.
* **Updater**: säkrare och bättre (se §3).

## 12. Anpassning per app

* Denna fil anpassas **efter varje app**: universella regler (§1–§7) följer
  med oförändrade till nästa app-repo, medan **[APP]**-reglerna (§8–§11)
  skrivs om efter den appens teknik och funktioner. Filen ligger alltid i
  repots rot.
