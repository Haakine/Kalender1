# Hendelseskalender

Abonnerbare kalendere (`.ics`) for Apple Kalender, publisert som en gratis, statisk nettside på GitHub Pages.

| Kalender | Innhold | Kilde |
|---|---|---|
| **Alle hendelser** | Alt under, samlet i én kalender med én farge | alle kildene under |
| Norges Bank: rentemøter | Rentebeslutninger, og dagene Pengepolitisk rapport kommer | [Norges Banks kalender](https://www.norges-bank.no/aktuelt/kalender/rentemoter/) |
| Federal Reserve: rentemøter | FOMC-avgjørelser (kl. 14:00 ET) og referatene tre uker senere | [federalreserve.gov](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm) |
| SSB: KPI og nøkkeltall | KPI, AKU (arbeidsledighet), produsentprisindeksen, konjunkturtendensene | [SSBs kommende publiseringer](https://www.ssb.no/en/kommende-publiseringer) |
| Fotball: Norges landslag | Herrelandslagets kamper med avspark i norsk tid | [sportsidioten.no](https://www.sportsidioten.no/fotball/nations-league-2026-2027/) og FotMob |
| Langrenn: verdenscup, NM og VM | Verdenscuprenn, Tour de Ski, Holmenkollen, NM og ski-VM i Falun | [FIS](https://www.fis-ski.com/cross-country/news/2025-26/tour-de-ski-to-make-french-debut-2026-27-world-cup-calendar-unveiled) og [Norges Skiforbund](https://prod.skiforbundet.no/globalassets/04-gren---medier/langrenn/regler-og-retningslinjer/2026-2027-sesonginformasjoner-langrenn.pdf) |
| Sjakk: VM og store turneringer | VM-matchen i Genève, parti for parti, og VM i rapid og blitz | [FIDE](https://www.fide.com/salesforce-fide-world-championship-match-2026-schedule-format-and-prize-fund-confirmed/) |

Datoene ble sjekket mot kildene 11. november 2026.

**Velg «Alle hendelser» eller de enkelte, ikke begge.** Abonnerer du på begge, dukker hver hendelse opp to ganger. «Alle» er enklest (én adresse), men har én farge og kan ikke slås av og på per tema. De enkelte kalendrene gir egen farge og av/på per tema.

## Publiser siden (ca. 10 minutter)

Du trenger en gratis GitHub-konto. Repoet må være **offentlig**: GitHub Pages fra private repoer krever betalt abonnement. Det er ikke noe problem her, siden alt i repoet er offentlige datoer.

1. Opprett et nytt, tomt repo på github.com (for eksempel `kalender`), satt til **Public**, uten README.
2. Last opp prosjektet. Enklest fra terminalen i mappen du har pakket ut:
   ```
   git init -b main
   git add .
   git commit -m "Første versjon"
   git remote add origin https://github.com/BRUKERNAVN/kalender.git
   git push -u origin main
   ```
   Hvis du heller laster opp via nettsiden: mappen `.github` er skjult på Mac og blir lett utelatt. Opprett i så fall filen manuelt med *Add file → Create new file*, sti `.github/workflows/pages.yml`, og lim inn innholdet fra den medfølgende filen.
3. Gå til **Settings → Pages**, og velg **Source: GitHub Actions**.
4. Gå til **Actions → Bygg og publiser kalendere → Run workflow**.
5. Siden ligger nå på `https://BRUKERNAVN.github.io/kalender/`.

**Ligger prosjektet i en undermappe i repoet** (for eksempel `kalender-feeds/`), må workflowen vite det. Legg da dette under `permissions:` i `pages.yml`, og endre `path: site` til `path: kalender-feeds/site`:
```yaml
defaults:
  run:
    working-directory: kalender-feeds
```

## Abonner

Åpne siden på iPhone, iPad eller Mac og trykk **Abonner i Kalender** på de kalendrene du vil ha. Apple henter nye datoer av seg selv, vanligvis med noen timers mellomrom.

Manuelt: *Mac: Arkiv → Ny kalenderabonnement*, eller *iPhone: Innstillinger → Kalender → Kontoer → Legg til konto → Annen → Legg til abonnert kalender*. Lim inn adressen `https://BRUKERNAVN.github.io/kalender/ics/alle.ics` (eller `norges-bank.ics`, `fed.ics`, `ssb.ics`, `fotball.ics`, `langrenn.ics`, `sjakk.ics`).

## Hva oppdateres automatisk, og hva gjør du selv?

Ærlig status:

- **Norges Bank:** Byggescriptet prøver å hente datoene fra Norges Banks kalenderside hver gang det kjører (hver mandag, og ved hver endring i repoet). Lykkes ikke hentingen, brukes datoene i `data/norges_bank.json`, og kjøringen feiler ikke. Hentingen er testet mot eksempel-HTML, men ikke mot den levende siden. Se på loggen fra en kjøring i Actions: den sier om datoene stemte eller om siden ikke kunne leses.
- **Alt annet oppdateres for hånd** i filene i `data/`. Det gjelder Fed, SSB og all sport. Sportskalenderne er sesongbaserte, og ingen åpne kilder jeg har verifisert gir dem som maskinlesbar feed.
- **Varsel når data går tom:** Jobben `freshness` feiler hvis Norges Bank, Fed eller SSB ikke lenger dekker langt nok frem (60, 90 og 21 dager). GitHub sender da vanligvis e-post om feilet kjøring. Sportsfeedene sjekkes ikke, siden de naturlig går tom mellom sesongene.

For å oppdatere en datafil: rediger den på github.com (blyantikonet), lagre, og siden bygges på nytt av seg selv.

## Hva er usikkert i sportsdataene?

- **Fotball:** Bare kampene som er publisert så langt er med (14. og 17. november 2026, to uavhengige kilder er enige). Nye landskamper må legges inn i `data/fotball.json` når datoene er klare.
- **Langrenn, verdenscup:** Dette er FIS' *foreslåtte* kalender fra mai 2026, som var avhengig av godkjenning i FIS-rådet. Jeg fant ikke en bekreftelse på at den ble vedtatt uendret. Renn legges inn som heldagshendelser, siden starttider ikke er publisert.
- **Langrenn, NM:** Datoene kommer fra Skiforbundets sesonginformasjon. NM-stafetten på Konnerud mangler fordi datoen ikke er oppgitt. Dokumentet oppgir 5 km/10 km på Hovden både som «lørdag 2. april» og «fredag 2. april». 2. april 2027 er en fredag, så jeg har brukt fredag.
- **Langrenn, VM:** Mesterskapet 24. februar–7. mars 2027 er bekreftet. Dagsprogram og starttider er ikke publisert, så det ligger inne som én hendelse over hele perioden.
- **Sjakk:** Partidatoene i VM-matchen (24. november–11. desember, omkamper 12. desember) kommer fra FIDE og en gjengivelse av tidsplanen. FIDE endret datoene for matchen i høst, og dette er de nye. Starttid for partiene er ikke oppgitt. **Tata Steel og Norway Chess 2027 er ikke med**, fordi jeg ikke fant bekreftede datoer. Legg dem til i `data/sjakk.json` under `events` når de er klare.

## Legge til en ny kalender

**Vanlig tilfelle: en liste med datoer. Ingen kode nødvendig.**

1. Kopier `data/custom/_mal.json` til `data/custom/<navn>.json` (på github.com: åpne malen, *Raw*, kopier, og bruk *Add file → Create new file*).
2. Fyll inn id, navn, beskrivelse, farge, gruppe og hendelsene. Malen viser heldag, flere dager og hendelse med klokkeslett.
3. Lagre. Siden bygges på nytt, og kalenderen får eget kort, egen `.ics`-adresse og kommer med i «Alle hendelser».

Gruppen styrer hvor kortet står på siden. Skriver du en ny gruppe, for eksempel «Kultur», får den en egen overskrift. Filer som begynner med `_` leses ikke. Testene stopper byggingen hvis en fil mangler felt, har ugyldige datoer eller bruker en id som finnes fra før.

**Når kilden trenger egen logikk** (henting fra nett, utregnede datoer, flere typer hendelser):

1. Lag en modul i `calfeeds/sources/` med `build_events(data)` som returnerer `Event`-objekter. `fed.py` er et eksempel med klokkeslett, `sjakk.py` med heldagshendelser.
2. Legg en datafil i `data/`.
3. Registrer en `Feed` i `calfeeds/feeds.py`.
4. Vil du at kilden skal hente nye data selv, legg til `refresh(data, today)` i modulen. Den får lagrede data og returnerer `(nye_data, notater)`. Se `norges_bank.py`: den beholder lagrede data hvis hentingen feiler. Byggescriptet kaller den automatisk.

I begge tilfeller trenger du ikke røre nettsiden, workflowen eller samlekalenderen.

**Bygge videre senere.** Slik kan større funksjoner legges til uten å endre grunnstrukturen:

- *Varsler om forskningsrapporter:* en modul med `refresh` som leser en åpen RSS-feed og lager hendelser fra utgivelsesdatoene. Vil du ha push-varsler i tillegg, kan en ukentlig workflow sende til en gratis ntfy-kanal.
- *Flere land eller lag:* kopier en eksisterende datafil og endre den.
- *TV-kanal på sendinger:* legg et felt i datafilen og ta det med i beskrivelsen.

## Trygghet og personvern

- Ingen server, database, innlogging eller sporing. Siden samler ikke inn noe om deg.
- Ingen hemmeligheter i koden. Kildene er offentlige sider og krever ingen API-nøkler.
- All tekst går gjennom escape og filtrering før den skrives i `.ics`-filene, så innhold fra en kilde ikke kan lage egne kalenderlinjer.
- Hendelsene er merket som «ledig», så de ikke gjør deg opptatt i kalenderen din.
- Siden har en streng innholdspolicy (CSP): ingen eksterne skript, skrifttyper eller bilder, og kun nøyaktig det innebygde skriptet og stilarket får kjøre.
- Prosjektet bruker bare Pythons standardbibliotek, så det er ingen avhengigheter å holde oppdatert. Hvis du vil stramme inn ytterligere, kan du låse GitHub Actions-stegene i `pages.yml` til commit-hasher og slå på Dependabot.

## Lokal kjøring

```
python3 -m unittest discover -s tests   # kjør testene
python3 build.py --offline              # bygg til site/ uten å hente fra nettet
python3 build.py --check-freshness      # sjekk at datoene dekker langt nok frem
```

Krever Python 3.9 eller nyere. Åpne `site/index.html` i nettleseren for å se siden. Abonner-knappene vises først når siden ligger på en nettadresse.

## Begrensninger

- Kalenderfeeder er enveis: Apple Kalender leser dem, men du kan ikke redigere hendelsene.
- Endringer i siste liten vises først når Apple henter feeden på nytt, ofte etter noen timer.
- Heldagshendelser (rennene, sjakkpartiene) har ikke klokkeslett. Når starttidene publiseres, kan de legges inn som vanlige hendelser.
- Tidspunkt: Norges Bank kl. 10:00 og SSB kl. 08:00 norsk tid, Fed kl. 14:00 amerikansk østkysttid. Kalenderen viser alt i din egen tidssone. USA og Norge bytter til sommertid på ulike datoer, så tidsforskjellen er én time kortere i noen uker i mars og oktober/november. Dette er håndtert i koden.
