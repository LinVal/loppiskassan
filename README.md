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
