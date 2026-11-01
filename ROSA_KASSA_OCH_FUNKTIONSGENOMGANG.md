# Rosa produktionskassa och funktionsgenomgång

## Ändring

Den skarpa kassans arbetsyta har fått en ljusrosa bakgrund (`#fcebf2`). Flikar, betalningspanel och bildminiatyrer har diskreta rosa toner. Kort och inmatningsfält är fortsatt vita för läsbarhet; primärknapparnas blå färg behålls. Demoläget är oförändrat. Ändringen gäller `static/index.html` och kräver ingen databasändring.

## Prioriterad funktionsgenomgång

1. **Köpflöde i verklig kassa (högst prioritet):** Prova A4, flera enskilda lappar, blandade bilder, felaktig AI-avläsning och manuell rättning i ett och samma köp. Säkerställ att antalet varor, summan och bilden förblir korrekta vid stegvxäxling och nätverksavbrott.
2. **Spårbarhet per vara:** Spara beständig koppling från varje varurad till originalfoto, AI-förslag och mänsklig korrigering. Nuvarande lokal koppling räcker inte för full historik.
3. **Betalning och avstämning:** Testa Swish, kort och kontant med manuell bekräftelse, felaktiga belopp, dubbla klick och avbrutna köp. Överväg separat dagsavstämning per kassa och betalningssätt.
4. **Behörigheter:** Nuvarande rollväljare ändrar endast synliga menyer. Inför serverstyrda roller innan kassapersonal får egna inloggningar.
5. **Mobilergonomi:** Testa kamera, bildgranskning och stora tryckytor på verkliga telefoner/surfplattor.
6. **Historik och rättelser:** Gör det möjligt att se alla originalbilder i försäljningshistoriken, med logg över behöriga korrigeringar.
7. **Tillgänglighet:** Kontrollera tangentbord, fokusmarkeringar, kontrast och skärmläsarstöd.

## Verifiering efter deploy

Öppna `/app`, välj **Skarpt läge → Kassan** och kontrollera rosa bakgrund. Växla till **Demoläge** och kontrollera att den tidigare bakgrunden finns kvar. Kontrollera därefter de fyra stegen, särskilt att betalning inte kan slutföras innan bekräftelse.
