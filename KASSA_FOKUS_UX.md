# Kassa – fokuserad granskning och säker betalning

- Originalbilden visas bredvid varulistan på större skärmar och ligger kvar vid skrollning.
- På mobil och surfplatta kan originalbilden öppnas och döljas för att ge mer plats åt varuraderna.
- Betalningssteget har en tydlig kontrollista för varor, mottagare, kontanter (vid kontantköp) och manuellt bekräftad betalning.
- Knappen för att granska/spara är inaktiv tills kontrollerna är uppfyllda. Den befintliga separata slutbekräftelsen och serverns validering finns kvar.
- Länken ”Administration / säljare / rapporter” är borttagen från kassans toppfält. Navigation sker via den gemensamma vänstermenyn på `/app`.
- Rollväljaren i gränssnittet är fortfarande en visningsfunktion och ersätter inte serverbaserad behörighetskontroll.

## Kontrollera efter deploy

1. Öppna `/app` på dator och granska varor med bilden till vänster.
2. Öppna på mobil och prova knappen ”Visa originalbild”.
3. Prova Swish, Kort och Kontant, inklusive otillräckligt kontantbelopp.
4. Kontrollera att spara-knappen kräver bekräftad betalning och att slutdialogen visas.
5. Verifiera återhämtning av avbrutet köp och att AI-granskning fortfarande fungerar.
