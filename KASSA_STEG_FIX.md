# Kassan: återställda steg och renodlat skarpt läge

## Rättningar
- Kassans UI-skript använde `items`, `sum`, `validPrice` och `refreshPhotoGallery` som var privata i ett annat JavaScript-scope. Det kunde avbryta initieringen av stegmenyn.
- UI-skriptet läser nu ett begränsat, skrivskyddat tillstånd från kassans huvudskript och uppdaterar bilder via en explicit funktion.
- Historiken i skarpt läge visar endast en länk till verklig försäljningshistorik i administrationen. Ingen lokal demohistorik, CSV-export eller knapp för att radera demohistorik visas där.
- Demoläget (`/demo`) har kvar sina övningsfunktioner.

## Kontroll efter deploy
1. Öppna `/app` och välj **Skarpt läge** och **Kassan**.
2. Kontrollera flikarna 1–4 och att bara en arbetsvy visas åt gången.
3. Kontrollera att steg 4 länkar till Administration → Försäljningar.
4. Växla till demoläge och kontrollera att exempelköpet fortfarande är tillgängligt.
5. Gör ett testköp mot ett isolerat testevenemang innan skarp användning.
