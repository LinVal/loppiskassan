# Permanenta säljaridentiteter – regler och flöden

- Ett **permanent person-ID** identifierar en säljare över flera evenemang.
- Ett **säljnummer** (1–250) är en tilldelning i ett visst evenemang.
- Två personer med samma namn får **inte** slås ihop automatiskt.
- Kopiering från tidigare evenemang bevarar person-ID även om säljnumret senare ändras.
- CSV kan ha extra kolumnen `person_id`; ett angivet ID måste finnas i registret.
- Om `person_id` saknas skapas en ny identitet för varje importerad rad.
- Tidigare tilldelningar migreras försiktigt till egna identiteter. De kopplas **inte** automatiskt ihop över gamla evenemang; administratören måste verifiera sådana samband.
- Ändring av tilldelning efter registrerad försäljning får inte byta person.
- API-adresserna `/api/v4/` och `/api/v5/` används fortfarande av befintligt gränssnitt. Vi behåller dem av tekniska skäl, men dokumenterar inte ett generellt löfte om bakåtkompatibilitet.

## Inför ett nytt evenemang
1. Skapa ett utkast.
2. Kopiera återkommande säljare från tidigare evenemang för att behålla person-ID.
3. Importera externa säljare med `nummer;namn;typ;person_id` där ID är valfritt.
4. Granska tilldelningarna och starta evenemanget.

## Begränsning
Historiska säljaruppgifter utan tidigare permanenta ID kan inte säkert sammanfogas automatiskt. Säljarens historiska försäljning förblir kopplad till evenemang och nummer; en fullständig identitetsbaserad historikrapport är ett separat steg.


## Sökbart personregister (administration)

I **Loppistillfällen → Tilldela säljnummer** kan administratören söka på namn, välja en befintlig person och se tidigare evenemang och säljnummer. Välj därefter ett ledigt nummer i det aktuella evenemanget och tilldela. Personens permanenta ID återanvänds.

Om ingen person väljs skapas en **ny identitet**, även om namnet är identiskt med en tidigare säljares. Detta är avsiktligt för att undvika felaktig sammanslagning. Kontrollera historiken innan en person väljs.

API: `GET /api/v5/seller-identities?q=...` (max 100 resultat som standard) och `GET /api/v5/seller-identities/{id}/history`. Historiken visar tilldelningar per evenemang, inte en sammanräkning av personens försäljning.

**Begränsning:** Äldre tilldelningar som redan migrerats till separata identiteter slås inte ihop automatiskt. För att få en sammanhållen historik krävs en separat, granskad sammanslagningsfunktion.
