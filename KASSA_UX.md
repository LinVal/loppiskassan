# Kassan – arbetsvyer

Kassan är nu uppdelad i fyra tydliga vyer: **Starta & skanna**, **Granska varor**, **Betalning** och **Historik**.

- Skanning: serverköp, mobilkoppling, bildhämtning och AI-analys.
- Granskning: originalbild, prislappar, säljar- och prisvalidering samt totalsammanställning.
- Betalning: totalsumma, ett betalningssätt, kontant växel och manuell bekräftelse.
- Historik: befintlig lokal demohistorik (inte serverbaserad avräkning).

Vyval sparas i sessionStorage. Befintliga DOM-id:n, kassans API-anrop och backend är oförändrade. Alla fyra vyerna finns på samma sida, men bara en visas åt gången. De befintliga stegen och statusmeddelandena är kvar.

## Kontroll efter deploy

1. Öppna `/app`, välj Kassan, starta ett nytt köp.
2. Fotografera eller ladda upp en bild och kör analys.
3. Gå till Granska varor; kontrollera att originalbild och alla rader visas, och att felaktiga priser markeras.
4. Gå till Betalning; kontrollera total, metod, kontant växel och bekräftelse. Spara ett testköp.
5. Växla mellan vyerna och kontrollera att köpdata ligger kvar.
6. Kontrollera surfplatta och mobil samt återställning av ett avbrutet köp.

**OBS:** Lokala automatiska tester verifierar inte visuella flöden i webbläsare. Rollväljaren är fortfarande en UI-demo och ger inte serverbehörighet.
