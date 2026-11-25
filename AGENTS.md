# AGENTS.md — Hårda regler för Tokke2/P-rm

Den här filen är den **enda sanningskällan** för arbetsregler i repot.
Varje ny chatt/agent ska läsa den **först** och följa alla regler utan
undantag. Regler markerade **HÅRD** får aldrig brytas.

---

## 1. Branch-reglerna (HÅRD)

* Repot ska alltid ha **exakt EN branch**: den aktuella arbetsbranchen
  (arena-branchen). `main` är borttagen och ska **aldrig** återskapas.
* Arbeta **aldrig emot main** — inte committa, inte pusha, inte bygga på den.
  Allt arbete sker **endast emot arbetsbranchen**, speciellt vid
  appuppdateringar och releaser.
* **Aldrig merge** — inte `git merge`, inte `gh pr merge`, inga mergar i någon
  form. Ändringar committas alltid direkt på arbetsbranchen.
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

## 7. Stående kvalitetskrav (återkommande — alltid beakta)

* **Skärpa & skärm**: skarp rendering vid alla DPI/skärmstorlekar — ingen
  grumlig text/bild/kolumn; tydliga typsnitt; layout som anpassar sig till
  skärmen; fönstret startar i max höjd-läge (beroende på skärm) med anpassad
  bredd; allt synligt, minimal scroll.
* **Design**: bättre logotyp (skarp, används överallt; vektor/redigerbar för
  tryck) och nya bättre ikoner.
* **Prestanda**: bättre minneshantering, snabbare, energisnålare.
* **Inställningar**: egen underflik för att skapa profiler (när
  profilstöd finns/skapas).
* **Underhåll**: arkiverade loggar rensas automatiskt efter **7 dagar**.
