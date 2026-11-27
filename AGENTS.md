# Arbetsregler för Pärmetikett Generator

Dessa regler gäller för detta repository och ska läsas vid varje nytt chatt-/arbetsbyte. De ersätter inte Arena-branchinstruktionen för den aktiva sessionen; de kompletterar den.

## 1. Branch, GitHub och arbetsflöde — hårda regler

- Arbeta enbart på den Arena-arbetsbranch som anges i den senaste branch-notisen. Kontrollera branch och status före ändringar.
- Arbeta aldrig mot `main`; byt aldrig branch och skapa aldrig en alternativ arbetsbranch.
- **Skapa aldrig pull request och merge aldrig.** Använd aldrig PR- eller merge-flöden.
- Pusha endast den aktiva Arena-arbetsbranchen, aldrig en annan branch.
- Ändra inte GitHubs default branch, radera brancher, skriv om historik eller flytta release-taggar automatiskt. Sådana repo-ägande åtgärder kan ta bort eller dölja andras arbete. Om standardbranch/branchstädning efterfrågas, förklara begränsningen och be om explicit val av vilken branch som ska bevaras innan destruktiv åtgärd.
- Om nuvarande branch ligger efter en publicerad release eller innehåller äldre funktioner, uppdatera inte `Latest` från den äldre kodbasen. Först behövs en säker, uttrycklig synkronisering på den tilldelade arbetsbranchen.
- Vid kodändring ska en lämplig versionerad GitHub Release hållas uppdaterad och markeras `Latest`, **men bara när releasen byggs från den verifierade, aktuella kodbasen**. Uppdatera aldrig en release genom att flytta en befintlig tagg till äldre/okänd kod. Om säker release inte kan göras, dokumentera varför i chatten.

## 2. Release och uppdaterare

- En framtida updaterare måste jämföra versionsmanifest och SHA-256 för varje distribuerad fil; nedladdning ska ske över HTTPS, valideras före installation och installeras atomiskt.
- Uppdateraren ska bevara återställningsmöjlighet tills den nya versionen har startat och klarat en hälsokontroll. Ta bort backup först efter verifierad lyckad uppdatering; återställ vid fel.
- Schemalagd kontroll ska vara energisnål, köras högst en gång per dygn vid lokal midnatt när appen/updateraren är igång, och får inte öppna terminalfönster. Ingen bakgrundsprocess får startas utan begriplig opt-out och säker felhantering.
- Lägg inte till en updaterare eller automatisk release som hämtar/kör obetrodd kod utan checksumma, versionskontroll och rollback.

## 3. Test och säkerhet

- Kör relevanta tester, statisk kontroll och kompilering före klarbesked. Lägg till regressionstest för varje buggfix där det är praktiskt möjligt.
- Bevara befintliga användarflöden och utskriftsmått; inga tysta beroende-, filformats- eller gränssnittsbrott. Dokumentera nya beroenden, valfria systemverktyg och begränsningar.
- Spara inställningar atomiskt. Begränsa inläsning av externa bild-/vektorfiler så att felaktiga eller mycket stora filer inte kan förbruka obegränsat minne.
- Håll PDF-text vektorbaserad. Använd högkvalitativ omsampling för rasterbilder och behåll vektororiginal redigerbara där det går. Undvik att skala upp lågupplösta bilder och kalla resultatet skarpt.
- GUI ska anpassas till skärmstorlek och DPI, vara läsbart och nåbart utan onödig scroll. Startfönstrets höjd anpassas till skärmen; bredd får inte gå utanför arbetsytan. Undvik terminalfönster i paketerade körningar.

## 4. Funktioner som bara gäller när appen redan använder dem

- Profiler: skapa en separat underflik för profiler endast om den här appen faktiskt har användarprofiler. Pärmetikett Generator har för närvarande inga färdiga profilflöden; lägg inte till en tom profilsida.
- Projekt-/rutval: återställ val av ruta/projekt endast om funktionen fanns i den aktuella appens tidigare ttk-version. Lägg inte till påhittad funktionalitet.
- Kolumnsortering/flytt: lägg till endast om appen har tabellkolumner.
- Loggpolicy: om appen får arkiverade loggar, arkivera gårdagens loggar och radera arkiv äldre än sju dagar. Håll separat app-logg och aktiv fellogg. Felloggen visar olösta fel; ta bort ett fel ur aktiv lista först när det verifierats åtgärdat, men behåll relevant historik i arkiv.
- Pärmetikett Generator har i nuläget varken updaterare, projektväljare, datagridskolumner eller aktiva profiler. Hitta inte på eller marknadsför sådana funktioner som implementerade.

## 5. Förslagslistor i chatten

- Förslag ska alltid skrivas i chatten, inte bara sparas i filer.
- Vid denna regeluppdatering: ge 25 konkreta, separata produktförslag. Efter var tionde användarmeddelande i en pågående konversation ska en ny lista med 10 förslag visas; återanvänd inte tidigare förslag. Om historik inte går att fastställa, säg det och ge en ny lista utan avsiktlig återanvändning.
- Förslagen ska vara relevanta för användarbehov och sakligt presenteras som idéer, inte som påståenden om att konkurrenter saknar dem utan verifiering.

## 6. Nuvarande produktscope

Pärmetikett Generator är en lokal Tkinter-app för rygg-, index- och verifikatetiketter till utskrift. Prioritera tydlig layout, skarp text och grafik, utskriftskorrekt PDF, tillgänglighet på små/stora skärmar, minnesbegränsning vid logotypimport och pålitlig lokal inställningshantering.
