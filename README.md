# Loppiskassan – GitHub + Heroku testversion

**Teknikprototyp, inte produktionsklar.** Mobilfoto → server → kassadator fungerar. AI-avläsning, verklig betalningsverifiering, riktig rollbaserad inloggning och offline-synk saknas. **Använd inga verkliga personuppgifter eller riktiga betalningar i testet.**

## Driftsätt via GitHub och Heroku

1. Skapa ett **privat GitHub-repo** och lägg upp filerna i denna mapp i repots rot (inte zip-filen). Lägg aldrig upp `.env`, lösenord eller API-nycklar.
2. Skapa en Heroku-app med **Python buildpack**, stack `heroku-24`, och koppla appen till ditt GitHub-repo via **Deploy → GitHub**. Välj branchen `main` och klicka **Deploy Branch**. Automatiska deployer är valfria.
3. Lägg till **Heroku Postgres** i Heroku Dashboard → Resources. Heroku tilldelar `DATABASE_URL` automatiskt. Starta inte en publikt driftsatt app utan Postgres: lokal SQLite försvinner vid dyno-omstart.
4. I **Settings → Config Vars** ange `DEMO_USER` och ett starkt, slumpmässigt `DEMO_PASSWORD`. Ange `PUBLIC_BASE_URL=https://DIN-APP.herokuapp.com` (byt till appens faktiska HTTPS-adress). Inga hemligheter i GitHub.
5. För bildlagring: konfigurera en **privat S3-bucket** och sätt `S3_BUCKET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`. Valfritt `S3_ENDPOINT_URL` för kompatibel tjänst. **Utan S3 sparas bilder på dynons tillfälliga disk och försvinner vid omstart** – använd då bara korta, ofarliga tester.
6. Öppna `https://DIN-APP.herokuapp.com`, logga in med demo-uppgifterna och testa **Starta serverköp → Koppla mobilkamera**. Skanna QR-koden med mobilens kamera (mobilen får använda eget mobilinternet). Efter uppladdning visas bilden på datorn; varorna läggs fortfarande in manuellt.
7. Kontrollera `https://DIN-APP.herokuapp.com/health` för enkel hälsokontroll. Läs loggar under **More → View logs**.

## Alternativ via Heroku CLI

```bash
heroku login
heroku create DIN-APP --stack heroku-24
heroku buildpacks:set heroku/python -a DIN-APP
heroku addons:create heroku-postgresql:essential-0 -a DIN-APP
heroku config:set DEMO_USER=demo DEMO_PASSWORD='BYT_TILL_STARKT_LÖSENORD' PUBLIC_BASE_URL=https://DIN-APP.herokuapp.com -a DIN-APP
# Lägg sedan till S3-variablerna via dashboard (inte i Git).
# Koppla GitHub-repot i Heroku Dashboard → Deploy → GitHub.
```

Herokus tillgängliga Postgres-planer och dyno-priser kan ändras. Välj en plan som finns i ditt konto. För staging/test kan en liten plan räcka; dimensionering för 10 samtidiga kassor måste belastningstestas.

## Viktiga begränsningar och säkerhet

- **HTTP Basic Auth är bara ett tillfälligt skydd för en begränsad testmiljö**, inte färdig autentisering. Mobilens engångslänk är publik för den som har token och gäller fem minuter. Dela inte QR-koder utanför personalen.
- Endast `/health`, `/mobile` och mobilens engångsuppladdning är undantagna från demo-inloggningen. Alla övriga vyer och API:er kräver demo-lösenordet.
- Denna prototyp skapar tabeller vid start. Inför produktion krävs migrationsverktyg, backup, riktiga roller och händelselogg.
- S3-objekt ska hållas **privata**; bilden levereras via ett autentiserat API. Ange lämplig gallringstid för personuppgifter och bilder.
- Ingen AI tolkar nya A4-ark ännu; inga köp ska betraktas som verifierade Swishbetalningar.
- Offlineköp, återupptagning efter stängd flik, skydd mot alla race conditions, 10-kassors belastningstest och skydd mot felaktiga/saknade lappar återstår.
- Lokal Docker är fortfarande användbart för utveckling, men behövs inte för Heroku-deploy.

## Lokal start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DEMO_USER=demo DEMO_PASSWORD='byt-mig'
uvicorn server:app --reload
```

Öppna `http://localhost:8000`. För mobiltest krävs en publikt nåbar HTTPS-adress.
