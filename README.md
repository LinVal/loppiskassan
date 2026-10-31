# Loppiskassan

Loppiskassan är en webbapp för flera kassor på samma loppis. Kassor kan registrera försäljningar, säljare kan se sin historik och administratörer kan hantera säljare, evenemang, provisioner och utbetalningar.

## Kodstruktur

- `server.py` – huvudapp, databas, kassa och API
- `sellers.py` – säljarregister, säljarportal, historik och justeringar (tidigare `v4_routes.py`)
- `events.py` – loppistillfällen, provisionsregler och utbetalningar (tidigare `v5_routes.py`)
- `staff_auth.py` – personalinloggning och behörighet
- `static/` – kassans, mobilens och administrationens gränssnitt
- `tests/` – automatiska tester
- `.github/workflows/tests.yml` – GitHub Actions med PostgreSQL

## Installera och testa

Installera beroenden med:

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
pytest -q
```

Starta lokalt med:

```bash
uvicorn server:app --reload
```

Lokalt används SQLite när `DATABASE_URL` inte är satt. GitHub Actions kör tester med en separat PostgreSQL-testdatabas.

## Driftsättning på Heroku

Behåll den befintliga Heroku-appen och dess tillägg för PostgreSQL och Bucketeer. Sätt hemliga nycklar i Heroku Config Vars, aldrig i GitHub. Säkerhetskopiera databasen före deploy.

Startkommandot finns i `Procfile`. Applikationen importerar nu `sellers.py` och `events.py`. **De tidigare filerna `v4_routes.py` och `v5_routes.py` ska tas bort från GitHub i samma commit som de nya filerna läggs till.**

## Bakåtkompatibilitet

De befintliga API-adresserna `/api/v4/...` och `/api/v5/...` är avsiktligt oförändrade så att webbläsargränssnitt och integrationer fortsätter fungera. Det är bara filnamnen i Python-koden som förenklats. Befintliga databastabeller och data ändras inte av namnbytet.

## Tester och begränsningar

GitHub Actions kör regressionstester och PostgreSQL-tester. Tester av återförsök simulerar förlorade HTTP-svar, inte faktiska nätverksavbrott. Ett nytt sessions-ID efter ett avbrott kan fortfarande skapa en dubblett. Kör testerna och kontrollera grönt resultat före Heroku-deploy.

Detta är fortfarande ett testsystem. Kontrollera behörigheter på API-nivå, betalningsflöden, säkerhetskopior och personuppgiftshantering före verklig drift.

Mer information om affärsregler finns i `REGLER_OCH_TESTER.md`.

## Återställning efter avbrott

Kassan sparar påbörjat köp och sessions-ID i webbläsarens `localStorage`. Vid omladdning kontrollerar den servern innan den återupptar köpet. Om köpet redan är registrerat rensas utkastet. Vid osäker nätverksstatus behålls utkastet; starta inte ett nytt köp förrän status har kontrollerats.

Detta skyddar mot vanliga omladdningar och upprepade anrop inom samma session, men är **inte fullständigt offlinestöd**. Lokal lagring är knuten till en viss webbläsare och kan raderas. Verifiera manuellt med två flikar, förlorad uppkoppling och flera kassor innan verklig drift.

## Gränssnittsdesign
Gemensamma designregler i `static/design-system.css` används av kassa, admin, säljare, evenemang och personal. Det är en första stylinguppdatering, inte en fullständig UX- eller WCAG-revision. Kontrollera gränssnitten visuellt före driftsättning.

## Kassaflöde

Kassan visar nu steg 1–4 (skanna, kontrollera, betala, klart), tydligare
felmeddelanden och en separat sammanfattning innan köpet skickas till servern.
Efter lyckad registrering visas en bekräftelse med möjlighet att starta nästa
kund. Om servern inte svarar behålls sessions-ID:t så att samma köp kan
försökas igen. Start av serverköp rensar de förifyllda demo-varorna.

**Viktigt:** Betalningen verifieras fortfarande manuellt. Ingen fullständig
offlineförsäljning finns. Testa visuellt och funktionellt innan användning.

## Fix: tom bildyta vid nästa kund
När serverköpet startas eller avslutas rensas både varulistan och fotoytan. Tidigare demobild ska inte visas för en ny kund. Vid återställning försöker kassan hämta den aktuella bildens serverkopia igen.

## UX-justeringar

- Manuellt tillagda prislappar är automatiskt markerade som kontrollerade.
  Säljnummer och pris måste fortfarande anges och valideras innan köpet sparas.
- AI-tolkade prislappar kräver fortfarande individuell granskning.
- Administrationen har sökfilter och antal synliga säljare.
- Säljarportalen visar registrerad försäljning tydligare utan att påstå att
  beloppet är en slutlig utbetalning.

Kontrollera GitHub Actions samt flödena manuellt före Heroku-deploy.

## Prisregel
Alla varupriser måste vara positiva hela kronor delbara med fem. Regeln
valideras i kassans gränssnitt och i serverns Pydantic-modell. AI-priser
som inte följer regeln markeras för korrigering, aldrig automatisk avrundning.
Befintliga försäljningar ändras inte.

## Prisfeedback i kassan

Priser valideras direkt medan kassapersonalen skriver. Ogiltiga prisfält
markeras med röd ram och ett tydligt meddelande. Köpknappen inaktiveras
tills alla priser är positiva femtal. Ingen automatisk avrundning görs.
Kassan öppnar nu utan förifyllda exempelvaror och med tom bildyta.
Serverns befintliga prisvalidering finns kvar som yttersta skydd.

## Exempelköp på kassans startsida

När ingen aktiv serverförsäljning finns visas originalets exempelbild och 19 exempelvaror. Klick på Starta serverköp tömmer bilden och varulistan. Nästa kund börjar också tomt. Vid omladdning av aktiv försäljning prioriteras sparat utkast. Exempelköpet är inte en riktig serverförsäljning.

### Nätverksavbrott i kassan

Kassan visar serverns anslutningsstatus (kontrolleras mot `/health` ungefär var tionde sekund).
Påbörjade serverköp lagras som utkast i webbläsarens `localStorage` och kan återställas
vid siduppdatering. Vid osäkert svar på sparat köp kontrolleras sessionsstatus innan
samma sessions-ID skickas på nytt. Serverns idempotenta registrering förhindrar
att samma session ger två försäljningar. Detta är **inte** fullständigt offlinestöd:
köp kan inte registreras på servern utan nätverksanslutning.

## Betalningsflöde 2.0
Se **KASSAFLODEN_OCH_KVALITETSREGLER.md** för fullständig processbeskrivning, kvalitetsregler, felhantering, ansvar och acceptanstester. Ett betalsätt per köp: Swish, Kort eller Kontant. Kontantbelopp valideras i både kassa och API; betalningar verifieras fortfarande manuellt.

## Kassaflöde 2.1 – evenemangstilldelningar och bildunderlag

Läs **KASSAFLODE_21_SYSTEMHANDBOK.md** för arbetsflöden, kvalitetsregler,
API och begränsningar. Nya evenemang skapas som utkast och måste startas
manuellt efter att namngivna säljnummer tilldelats. Befintliga öppna
evenemang påverkas inte automatiskt av denna ändring; tilldela deras
säljnummer innan ytterligare försäljning registreras.
