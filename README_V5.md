# Loppiskassan v5 – loppistillfällen, provision och slutavräkning

## Nytt
- Skapa separata loppistillfällen via `/events` (länk i `/admin`). Högst ett öppet loppistillfälle åt gången.
- 25 % standardprovision per säljare, redigerbar 0–100 %.
- Provisionssatsen sparas på varje varurad vid köpet. Ändringar i säljarregistret ändrar inte historiska köp.
- När loppisen avslutas stoppas nya köp och korrigeringar för tillfället.
- Slutavräkning per säljare, CSV och manuell markering av en slututbetalning per säljare.
- **Ingen automatisk överföring av pengar.**

## Uppgradering från v4
1. Säkerhetskopiera PostgreSQL: `heroku pg:backups:capture -a loppiskassan` och verifiera att backupen skapades.
2. Kopiera filerna i denna mapp till **roten** av samma GitHub-repository som tidigare och driftsätt via Heroku.
3. Öppna `/events` och skapa ett loppistillfälle **innan nästa testköp**.
4. Sätt individuella provisioner innan du gör köp. Kontrollera slutavräkningen före avslut.

## Historiska köp
Tidigare köp förs till det **avslutade** tillfället `Tidigare försäljningar (före v5)` och tilldelas **25 %** provisionssats som ett tekniskt standardvärde, eftersom äldre versioner inte sparade provisionssatser. Dessa belopp måste granskas manuellt före verklig avräkning. Äldre köp omräknas inte när provision ändras.

## Viktiga begränsningar
- Fortfarande **testversion** med gemensamt Basic Auth-lösenord, inte redo för riktiga personuppgifter eller pengar.
- Belopp anges i hela kronor; provision avrundas per varurad till närmaste krona (halva uppåt).
- En redan markerad utbetalning kan inte ändras via UI. Kontrollera belopp och mottagare noga innan du markerar.
- CSV öppnas i Excel. Ingen `.xlsx`-fil genereras.
- Flera samtidiga kassor har ännu inte belastningstestats.
- V4-säljarportalen visar fortfarande bruttoförsäljning; v5-slutavräkningen finns i administrationen.
- Migrationen sker vid appstart och använder PostgreSQL advisory lock. För produktion bör schemaändringar flyttas till versionsstyrda databasmigreringar.
