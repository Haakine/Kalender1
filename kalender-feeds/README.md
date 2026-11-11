# Hendelseskalender

Abonnerbare kalendere (`.ics`) for Apple Kalender, publisert som en gratis, statisk nettside på GitHub Pages.

Første versjon har tre kalendere:

| Kalender | Innhold | Kilde |
|---|---|---|
| Norges Bank: rentemøter | Rentebeslutninger, og dagene Pengepolitisk rapport kommer | [Norges Banks kalender](https://www.norges-bank.no/aktuelt/kalender/rentemoter/) |
| Federal Reserve: rentemøter | FOMC-avgjørelser (kl. 14:00 ET) og referatene tre uker senere | [federalreserve.gov](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm) |
| SSB: KPI og nøkkeltall | KPI, AKU (arbeidsledighet), produsentprisindeksen, konjunkturtendensene | [SSBs kommende publiseringer](https://www.ssb.no/en/kommende-publiseringer) |

Datoene ble sjekket mot kildene 11. november 2026.

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
4. Gå til **Actions → Bygg og publiser kalendere → Run workflow**. (Første push kjører den også, men feiler hvis du ikke hadde gjort steg 3 først. Da kjører du den bare på nytt.)
5. Siden ligger nå på `https://BRUKERNAVN.github.io/kalender/`.

## Abonner

Åpne siden på iPhone, iPad eller Mac og trykk **Abonner i Kalender** på de kalendrene du vil ha. Hver kalender får eget navn og farge, og kan slås av og på uavhengig av de andre. Apple henter nye datoer av seg selv, vanligvis med noen timers mellomrom.

Manuelt: *Mac: Arkiv → Ny kalenderabonnement*, eller *iPhone: Innstillinger → Kalender → Kontoer → Legg til konto → Annen → Legg til abonnert kalender*. Lim inn adressen `https://BRUKERNAVN.github.io/kalender/ics/norges-bank.ics` (tilsvarende `fed.ics` og `ssb.ics`).

## Hva oppdateres automatisk, og hva gjør du selv?

Ærlig status for første versjon:

- **Norges Bank:** Byggescriptet prøver å hente datoene fra Norges Banks kalenderside hver gang det kjører (hver mandag, og ved hver endring i repoet). Lykkes ikke hentingen, brukes datoene i `data/norges_bank.json`, og kjøringen feiler ikke. Hentingen er testet mot eksempel-HTML, men ikke mot den levende siden, så se på loggen fra første kjøring i Actions: den sier om datoene stemte eller om siden ikke kunne leses.
- **Fed og SSB:** Datoene ligger i `data/fed.json` og `data/ssb.json` og oppdateres for hånd. Fed publiserer neste års kalender omtrent ett år i forveien, og 2027-datoene er foreløpige til Fed bekrefter dem. SSBs kalender dekker bare noen måneder frem, så SSB-feeden når til 9. februar 2027.
- **Varsel når data går tom:** Jobben `freshness` feiler hvis en feed ikke lenger dekker langt nok frem i tid (Norges Bank 60 dager, Fed 90, SSB 21). GitHub sender da vanligvis e-post om feilet kjøring. Du kan skru varslene av og på under dine varslingsinnstillinger på GitHub.

For å oppdatere en datafil: rediger den på github.com (blyantikonet), lagre, og siden bygges på nytt av seg selv.

## Legge til en ny kilde

1. Lag en modul i `calfeeds/sources/` med en `build_events(data)`-funksjon som returnerer `Event`-objekter (se `fed.py` som mal).
2. Legg en datafil i `data/`.
3. Registrer feeden i `calfeeds/feeds.py`.

Neste kilder på planen: sport (landslaget i fotball, langrenn, sjakk) og varsler om forskningsrapporter.

## Trygghet og personvern

- Ingen server, database, innlogging eller sporing. Siden samler ikke inn noe om deg.
- Ingen hemmeligheter i koden. Kildene er offentlige sider og krever ingen API-nøkler.
- All tekst går gjennom escape og filtrering før den skrives i `.ics`-filene, så innhold fra en kilde ikke kan lage egne kalenderlinjer.
- Hendelsene er merket som «ledig», så de ikke gjør deg opptatt i kalenderen din.
- Siden har en streng innholdspolicy (CSP): ingen eksterne skript, skrifttyper eller bilder, og kun nøyaktig det innebygde skriptet får kjøre.
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
- Tidspunkt: Norges Bank kl. 10:00 og SSB kl. 08:00 norsk tid, Fed kl. 14:00 amerikansk østkysttid. Kalenderen viser alt i din egen tidssone. USA og Norge bytter til sommertid på ulike datoer, så tidsforskjellen er én time kortere i noen uker i mars og oktober/november. Dette er håndtert i koden.
