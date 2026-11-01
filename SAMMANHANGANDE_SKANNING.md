# Sammanhängande skanning – produktionskassan

- Steg 1 heter Skanna varor. Klick på Skanna med mobilen skapar serverköp om inget finns och visar QR-kod.
- Mobilfoton hämtas via befintlig polling och behandlas automatiskt av AI, en bild i taget.
- Varje foto får högst en automatisk AI-behandling i aktuell webbläsarsession. Felade foton kan provas igen manuellt.
- Samtliga AI-rader kräver fortsatt manuell kontroll före betalning.
- Enskilda fel stoppar inte efterföljande foton.

## Viktigt före drift

Testa QR-kod, flera mobilfoton, AI-fel, omladdning, kassaidentitet och fullständigt köp på en testmiljö. Automatiska API-anrop från flera öppna flikar kan fortfarande kräva starkare serverbaserad idempotens.
