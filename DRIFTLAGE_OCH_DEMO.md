# Skarpt läge och demoläge

## Skarpt läge
I `/app` väljs **Skarpt läge** i vänstermenyn. Kassan laddar `/` utan exempelvaror och utan lokal demohistorik. Försäljning kräver ett riktigt serverköp och betalningsbekräftelse. Tidigare påbörjade serverköp kan återställas enligt befintligt kassaflöde.

## Demoläge
Välj **Demoläge – utbildning**. Kassan laddar `/demo`, en separat sida som inte innehåller kod för serverköp, bildöverföring eller AI-anrop. Den använder det tidigare lokala exempelköpet med 19 varor och sparar bara övningshistorik i webbläsarens localStorage. Inga övningsköp registreras på servern. Foto kan laddas upp lokalt och varor läggas till manuellt. Demo stödjer ännu inte mobilkoppling eller AI.

## Roller och säkerhet
**Visa menyer som** (Kassapersonal/Administratör) är fortsatt en demonstrationsväljare och är **inte autentisering**. Kassaläget är ett gränssnittsval, inte en serverbehörighet. Den skarpa servern behåller sina existerande autentiseringskrav. Riktiga serverbehörigheter för kassapersonal och administratörer återstår att införa.

## Kontroll efter deploy
1. Öppna `/app` i skarpt läge: ingen exempelbild, inga exempelvaror, ingen demohistorik.
2. Växla till demo: 19 exempelvaror, lokal övningsbetalning, ingen nätverksregistrering.
3. Växla tillbaka: demoresultat får inte synas i skarp kassa.
4. Kontrollera att riktiga köp fortfarande kräver serverköp, giltiga priser och bekräftad betalning.
5. Kontrollera mobil och surfplatta i riktig webbläsare.
