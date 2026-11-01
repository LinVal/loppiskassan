# Administration – samlad navigation

## Två huvudingångar
- **Kassan**: `/`
- **Administration**: `/admin`

`/events` leder till administrationsvyn för loppistillfällen.

## Meny
Översikt, Loppistillfällen, Säljartilldelning, Säljarregister, Försäljningar, Provision, Slutavräkning, Rapporter och Korrigeringslogg. Varje funktion har en egen vy och direktlänk via `#` i webbadressen.

## Tekniskt upplägg
Detta är en **SPA-liknande administrationsskal** med separata befintliga vyer i isolerade inbäddade dokument. Det är avsiktligt en försiktig övergång, inte en omskrivning till ett JavaScript-ramverk. Befintliga API:er, behörighetskontroller och formulär är oförändrade. Interna moduladresser är `/admin/module` och `/events/module`.

## Kvalitetskontroll före skarp användning
Testa varje menyvy, direktlänkar, mobilvy, CSV-import, tilldelning, startkontroll, provisionsändring, köpjustering och utbetalningsmarkering med testdata. Kontrollera också att endast administratörer kan nå dessa vyer. Ingen databasändring krävs av navigationsändringen.

## API-versioner
Tekniska API-sökvägar behålls oförändrade för att inte bryta kassans anrop. Gamla versionsetiketter ska inte visas som produktinformation i gränssnittet.
