# Loppiskassan v4 – GitHub + Heroku

Uppdatering av fungerande v3. Behåller QR-mobilkamera, Bucketeer/S3, AI-avläsning, befintligt kassagränssnitt och PostgreSQL. Lägger till säljarregister, privat läsportal, gemensam försäljningshistorik, rapporter, CSV och spårbara justeringar.

## Installera

1. Packa upp ZIP-filen och **ersätt filerna i ditt befintliga privata GitHub-repository**. Behåll befintlig Heroku-app och PostgreSQL. Publicera samma GitHub-branch i Heroku (Deploy Branch eller automatisk deploy).
2. Behåll `DEMO_USER`, `DEMO_PASSWORD`, `PUBLIC_BASE_URL=https://loppiskassan-07d30648d332.herokuapp.com`, `OPENAI_API_KEY`, `OPENAI_MODEL` och de automatiska `BUCKETEER_*`-variablerna. Lägg **inte** API-nycklar i GitHub.
3. Kontrollera `/health`, kassan `/`, administration `/admin` och QR-fotografering. Tabellen skapas automatiskt. Säkerhetskopiera Postgres före driftsättning.
4. Registrera säljare under `/admin`. Klicka **Skapa privat länk** och dela länken med respektive säljare. En ny länk spärrar föregående. Portalen är läsbar utan personalens Basic Auth, men kräver den hemliga länken.
5. Registrera ett testköp i kassan och kontrollera att det syns i `/admin` och i rätt säljares portal. Gör en testkorrigering och kontrollera CSV/rapporter.

## Funktioner och viktiga begränsningar

- `/admin`: säljarregister (nummer, namn, e-post, telefon, aktiv), historik med varurader, korrigeringar med namn/orsak och rapporter per säljare/kassa/betalsätt/dag.
- `/seller?token=...`: läsportal för en säljare, visar registrerade varor och netto. Länken är en hemlig åtkomstnyckel – skicka den privat och dela inte i offentliga kanaler. Den kan återkallas genom att skapa en ny.
- 10 kassor kan använda samma PostgreSQL; transaktioner och unikt session-ID hindrar dubbelsparande av samma köp. **Ingen belastningstest med 10 samtidiga kassor har utförts.**
- Historik och rapporter hämtas från servern. Det äldre kassagränssnittets *lokala demohistorik* är fortfarande bara webbläsardata – använd `/admin` för verklig serverhistorik.
- Korrigeringar läggs till som separata poster, originalköp skrivs inte över. Inga återbetalningar utförs automatiskt. Netto per säljare och kassa tar hänsyn till justeringar. Dagsrapportens korrigeringar visas efter korrigeringsdatum i UTC, inte nödvändigtvis samma dag som köpet.
- Säljnummer på prislappar **matchas inte automatiskt mot säljarregistret vid köp** ännu. Registrera och kontrollera säljnummer före verklig användning.
- Fortfarande **testsystem**: Basic Auth är delad mellan personal, portalens länkar kan vidarebefordras, ingen rollstyrning/individuell kassainloggning, ingen Swish-verifiering, ingen automatisk avräkning, ingen robust offline-synk och ingen GDPR-granskning. Använd inte för riktiga person- eller betalningsuppgifter utan säkerhetsgenomgång.
- Heroku-app och Bucketeer kan lagra uppgifter i USA. Granska personuppgiftsbiträdesavtal och lagringsregion innan riktig drift.

## Lokalt

```bash
python -m pip install -r requirements.txt
export DEMO_USER=test
export DEMO_PASSWORD='byt-mig'
uvicorn server:app --reload
```

SQLite används lokalt utan `DATABASE_URL`. S3/Bucketeer krävs för att bilder ska överleva omstarter på Heroku.
