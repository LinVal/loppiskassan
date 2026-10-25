# Loppiskassan – affärsregler och teststrategi

## Affärsregler (v5)
1. Nya säljare har **25 % provision**. Individuell provision är 0–100 %.
2. Provision sparas per **varurad vid köpögonblicket**. Ändrad säljarprovision får inte påverka tidigare varor.
3. Beräkning görs i **hela kronor, per varurad**, med avrundning HALF_UP. Provision + säljarandel = varuradens nettobelopp.
4. Varje försäljning kräver en aktiv loppis, en existerande aktiv säljare och manuellt bekräftad betalning.
5. Ett köp får inte dubbelregistreras vid återförsök med samma sessions-ID.
6. Ett loppistillfälle måste avslutas innan utbetalning får markeras. Avslut låser nya försäljningar och korrigeringar.
7. Utbetalning är **en manuell bokföringsmarkering**, aldrig en faktisk pengaöverföring. Samma säljare/loppis får inte markeras utbetald två gånger.
8. Korrigeringar loggas med orsak och aktör. En varurads nettobelopp får inte bli negativt.
9. AI-tolkning är endast ett förslag. Personal måste jämföra samtliga lappar mot originalbilden och bekräfta betalningen.
10. Historiska köp före v5 tillhör en särskild avslutad loppis; deras provisionssats kan vara ett antaget standardvärde och måste granskas.

## Testnivåer
- **Enhetstester:** provision, avrundning och validering.
- **API-/integrationstester:** köp, provisionens historik, korrigeringar, låsning, slutavräkning, utbetalning, autentisering.
- **Separat framtida PostgreSQL-test:** samtidiga köp, låsning och transaktioner. SQLite-testerna ersätter **inte** detta.
- **Separat AI-regressionstest:** anonymiserade referensbilder med förväntat antal lappar, säljnummer och priser. Kör manuellt eller med mockad AI i CI för att undvika kostnader och icke-determinism.
- **Separat webbläsartest:** QR-parning, mobiluppladdning och granskningsflöde på mobil/dator.

## Lokal körning
```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
pytest -q
```

## Inför driftsättning
1. Ta en Postgres-backup på Heroku.
2. Skapa pull request till GitHub. Kontrollera att GitHub Actions blir grön.
3. Kör manuellt ett testköp och kontrollera att **inga riktiga betalningar** utförs.
4. Driftsätt först därefter.

## Kända begränsningar
- Testerna använder en **tillfällig lokal SQLite-databas**, aldrig Heroku/Postgres eller Bucketeer.
- Fullständigt samtidighetsskydd, rollbaserad åtkomst, migrationsverktyg och robust återställning återstår.
- Det befintliga systemet har fortfarande temporärt gemensamt testlösenord. Inte redo för riktiga personuppgifter eller betalningsdrift.
