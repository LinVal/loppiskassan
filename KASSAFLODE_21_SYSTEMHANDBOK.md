# Loppiskassan – Kassaflöde 2.1: systemhandbok

## Roller och principer

- Administratören skapar loppistillfällen, tilldelar säljnummer och öppnar/stänger evenemang.
- Kassapersonalen registrerar varor och bekräftar betalningar.
- Ett säljnummer är **endast giltigt inom sitt evenemang**. Numret kan återanvändas vid senare evenemang.
- Säljartypen `staff` eller `external` är metadata; **inga nummerintervall är reserverade i koden**.
- Högst 250 säljnummer (1–250) i denna version. Det är tillåtet att använda färre.

## Flöde A – förbered loppisen

1. Skapa loppistillfälle under **Loppistillfällen**. Det får status **utkast** (`draft`).
2. Välj evenemanget och tilldela säljnummer, namn och typ (medarbetare/extern).
3. Lediga nummer lämnas helt enkelt otilldelade.
4. Välj **Starta loppis**. Systemet kräver minst en tilldelad, namngiven säljare och att ingen annan loppis är öppen.
5. Evenemanget får status **pågående** (`open`). Försäljning kan nu registreras.
6. Administratören kan tilldela fler lediga nummer under pågående evenemang. Ändringar loggas.
7. Avsluta evenemanget efter loppisen. Stängningen låser ändringar och möjliggör avräkning.

**Kvalitetsregler:** Ett nummer får bara ha en tilldelning per evenemang. En säljare som redan har försäljning på sitt nummer får inte bytas mot ett annat namn. Ett tilldelat nummer kan frigöras i utkastläget, inte efter start. Samma nummer kan ha olika namn i olika evenemang.

**Begränsning:** Tilldelningar är separata från det äldre globala säljarregistret. En säljare behöver fortfarande finnas och vara aktiv där för att en försäljning ska kunna genomföras. Provision hämtas tills vidare från det globala registret. Automatiskt kopieringsflöde för återkommande säljare är ännu inte implementerat.

## Flöde B – kassaförsäljning

1. Starta serverköp. Exempelköpet i startsidan är en demonstration och ska inte sparas som en riktig försäljning.
2. Fotografera etikettarket eller registrera varor manuellt.
3. Kontrollera säljar-ID, beskrivning och pris mot originalet. AI-förslag är inte facit.
4. Priser måste vara positiva heltal delbara med fem.
5. Vid sparande kontrollerar servern att varje säljnummer är **tilldelat i det öppna evenemanget** och finns som aktiv säljare i grundregistret.
6. Granska totalsumma och välj ett betalsätt: Swish, kort eller kontant.
7. Personalen bekräftar manuellt att betalningen faktiskt är mottagen och sparar köpet.
8. Samma sessions-ID kan inte skapa flera försäljningar; upprepade försök returnerar tidigare köp.

**Kvalitetsregler:** Lediga nummer stoppas. Ogiltiga priser stoppas. Betalning får inte bekräftas automatiskt bara för att kunden säger sig ha betalat. Vid nätverksproblem måste köpstatus kontrolleras innan man försöker ta betalt igen.

## Flöde C – originalbilder och efterkontroll

- Vid mobiluppladdning sparas originalbildens byteinnehåll i privat Bucketeer/S3 om detta är konfigurerat. I lokal testmiljö används disk.
- En bild kopplas till ett serverköp via `session_id` i tabellen `photos`.
- En avslutad försäljning är kopplad till samma `session_id`. Administrations-API:et `/api/v4/sales` innehåller nu `photos` med interna bildlänkar per försäljning.
- Originalbilderna raderas inte när kassapersonalen väljer **Nästa kund**.
- Vid efterkontroll kan en administratör öppna den kopplade bilden och jämföra mot registrerade varor.

**Begränsningar att känna till:** Bilden lagras när den laddas upp, inte först vid slutbetalning. Manuellt registrerade varor kan sakna bild. Denna version sparar inte AI:s råförslag och alla efterföljande fältändringar som separat revisionshistorik. Den kräver inte foto för att få spara ett manuellt köp. Kontrollera Bucketeer-konfigurationen på Heroku: lokal dyno-disk är inte varaktig arkivlagring. Sätt en policy för lagringstid och behörig åtkomst till bilder.

## Flöde D – när något går fel

| Händelse | Systembeteende / personalens åtgärd |
|---|---|
| Okänt eller ledigt säljnummer | Servern avvisar köpet. Kontrollera lappen eller be administratören tilldela numret. |
| Ett tilldelat nummer saknar namn | Kan inte skapas via tilldelnings-API:et. |
| Ingen tilldelad säljare vid start | Start blockeras. |
| En annan loppis pågår | Nytt evenemang kan inte startas. |
| Fel pris, exempelvis 12 kr | Fältvalidering och servervalidering stoppar priset. |
| Dubbelklick på Spara | Sessions-ID ger idempotent försäljning. |
| Nätverksavbrott efter betalning | Kontrollera serverns köpstatus innan någon ny betalning tas. |
| Misstänkt felläsning efter köp | Sök fram försäljningen och öppna dess bildlänkar. |

## API och testning

- `POST /api/v5/events` – skapa utkast.
- `GET /api/v5/events/{id}/sellers` – lista tilldelade och antal lediga.
- `PUT /api/v5/events/{id}/sellers` – tilldela eller uppdatera ett nummer.
- `DELETE /api/v5/events/{id}/sellers/{number}` – frigör nummer före start.
- `POST /api/v5/events/{id}/start` – startkontroll och öppning.
- `POST /api/v5/events/{id}/close` – avsluta.
- `GET /api/v4/sales` – köphistorik inklusive `photos`.

Automatiska tester täcker bland annat utkast, startspärr, lediga nummer, förbud mot ägarbyte efter försäljning, betalning och idempotens. Fullständig browsergenomgång och Heroku-test återstår.

## Import och återanvändning av säljare

**Syfte:** Förbereda en ny loppis utan att registrera varje återkommande säljare manuellt.

**CSV-import:** Gå till *Loppistillfällen*, skapa eller välj ett **utkast** och välj CSV-filen. Filen ska vara UTF-8 och innehålla rubrikerna `nummer;namn;typ`. `typ` är valfri och får vara `medarbetare` eller `extern` (alternativt `staff`/`external`). Om typ saknas används extern. Excel-arbetsböcker (.xlsx) behöver först exporteras till CSV. Nummer 1–250 är möjliga; lediga nummer får sakna tilldelning.

Exempel:

```csv
nummer;namn;typ
1;Anna Andersson;medarbetare
78;Erik Eriksson;extern
```

**Kopiering:** Välj det nya utkastet som mål, välj tidigare evenemang som källa och välj *Medarbetare*, *Externa* eller *Alla*. Kopierade nummer och namn är ett förslag för det nya evenemanget, inte en permanent reservation. Administratören kan frigöra eller ändra dem före start.

**Kvalitetsregler:**
- Import och kopiering är bara tillåtna i utkast.
- Tomma namn, nummer utanför 1–250, dubbla nummer i samma fil och okänd säljartyp stoppas.
- Befintliga tilldelningar skrivs inte över. Vid konflikt avbryts hela importen/kopieringen utan delvis genomförda tilldelningar.
- Ändringar i tilldelningar loggas med aktör och tidpunkt.
- Saknas säljnumret i grundregistret skapas det automatiskt. Finns det redan bevaras grundregistrets namn och provision; ett inaktivt nummer blockerar importen. Detta innebär att grundregistrets namn kan skilja sig från namnet i ett evenemang och behöver granskas av administratör.
- Kopiering eller import startar aldrig loppisen automatiskt. Startkontrollen måste fortfarande passera.

**Begränsning:** Detta är CSV-import, inte direktimport av .xlsx. Systemet har ännu ingen separat global personidentitet för återkommande säljare; återanvändning sker via säljnummer och evenemangstilldelningar. Det är viktigt vid byte av nummer och framtida vidareutveckling.

**Testfall:** CSV med medarbetare och externa, kopiering till nytt utkast, dubbla nummer, upptaget nummer, ogiltigt namn/nummer/typ samt import efter start.
