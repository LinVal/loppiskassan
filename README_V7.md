# Loppiskassan v7 – PostgreSQL-test för 10 samtidiga kassor

Denna version behåller v6-applikationen och lägger till `tests/test_postgres_concurrency.py` samt en GitHub Actions-workflow med en **tillfällig PostgreSQL 16-databas**. Ingen ytterligare Heroku-app behövs.

## Vad testas?

- 10 samtidiga kassor, vardera med 100 köp (totalt 1 000).
- 1 000 unika köp och sessioner; exakt 100 köp per kassa.
- Summan 100 000 kr, provision 25 000 kr och säljarandel 75 000 kr vid 25 % provision.
- Varje varurad har säljare 77 och lagrad provision 2 500 baspunkter.
- Två samtidiga försök att spara samma session ger **ett** köp (idempotens).
- Befintliga v6-tester körs också.

## GitHub

Kopiera filerna i detta paket till ditt befintliga repository, inklusive den dolda `.github`-mappen. Skapa en commit. Under **Actions → Tester** ser du resultatet. Om testet misslyckas ska du inte deploya förrän orsaken är undersökt.

GitHub Actions skapar automatiskt en ny PostgreSQL-service för jobbet och förstör den efteråt. Den ansluter inte till din Heroku-databas. Körning kan ta ett par minuter.

## Lokalt (frivilligt)

Installera beroenden med `pip install -r requirements.txt -r requirements-dev.txt` och kör `pytest -q` för SQLite-regressionerna. PostgreSQL-testet hoppas över utan `TEST_DATABASE_URL`. För fullständigt test, skapa en **tom, lokal PostgreSQL-databas** och sätt exempelvis `TEST_DATABASE_URL=postgresql+psycopg://loppis_test:ci-only-password@localhost:5432/loppis_test` innan `pytest -q`.

## Begränsningar

Detta är ett integrationstest, inte ett komplett prestanda- eller säkerhetstest. Det mäter inte svarstider under en hel dag, nätverksavbrott eller verklig Heroku-kapacitet. Testdatabasen måste vara tom eftersom applikationen initierar tabeller vid import. Den nuvarande appens inloggning med HTTP Basic är fortfarande endast avsedd för utveckling.
