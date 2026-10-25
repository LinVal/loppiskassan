# Loppiskassan v3 — Heroku, Bucketeer och AI

## Nytt i version 3
- Bilder lagras i **privat Bucketeer** via de automatiska `BUCKETEER_*`-variablerna.
- `OPENAI_API_KEY` aktiverar knappen **Läs prislappar med AI** efter ett mobilfoto.
- Alla AI-rader markeras för manuell kontroll. AI kan missa lappar. Ingen försäljning sparas av AI.
- UTF-8-fix för svenska tecken i demo-inloggningen.

## Uppdatera befintligt GitHub-repository
Packa upp ZIP och kopiera filerna till roten av ditt befintliga GitHub-repository. Ersätt `server.py`, `requirements.txt`, `static/index.html` m.fl. Committa och välj Deploy Branch i Heroku om automatisk deploy inte är på.

## Heroku Config Vars
Heroku har redan skapat `DATABASE_URL` och följande från Bucketeer:
- `BUCKETEER_BUCKET_NAME`
- `BUCKETEER_AWS_ACCESS_KEY_ID`
- `BUCKETEER_AWS_SECRET_ACCESS_KEY`
- `BUCKETEER_AWS_REGION`

Behåll `DEMO_USER`, `DEMO_PASSWORD` och `PUBLIC_BASE_URL`. Lägg till:
- `OPENAI_API_KEY` = din hemliga API-nyckel (lägg **inte** i GitHub)
- `OPENAI_MODEL` = `gpt-4.1-mini` (valfri)

**Viktigt:** OpenAI API-fakturering är separat från ChatGPT-abonnemang. Bilder skickas till AI-tjänsten när du klickar på knappen. Använd enbart testdata tills du har gått igenom dataskydd och behörigheter.

## Testa
1. Starta serverköp på datorn.
2. Koppla mobilen med QR-kod och fotografera A4-arket.
3. Bilden visas på datorn och lagras privat i Bucketeer.
4. Klicka **Läs prislappar med AI**.
5. Jämför antal lappar, säljnummer och priser med originalbilden. Rätta och markera rader som kontrollerade.
6. Bekräfta betalningen manuellt och spara serverköpet.

## Begränsningar
- Testprototyp, inte färdig produktionskassa. Basic Auth är gemensam för alla kassor.
- Mobillänkar är engångstoken. Håll länkar privata.
- AI-resultat kan vara fel eller missa lappar; kräver manuell kontroll.
- HEIC kan lagras, men AI kräver JPEG/PNG i denna version.
- Lokal lagring används om ingen S3/Bucketeer är konfigurerad och försvinner vid dyno-omstart.
- PostgreSQL-tabeller skapas fortfarande vid import. Kör en webbarbetare under testerna; använd databasmigreringar före skarp drift.
- Ingen automatisk betalningsverifiering, ingen riktig offline-synkronisering.
