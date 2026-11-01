# Skanna flera prislappar i samma köp

1. Starta ett serverköp och koppla mobilen med QR-koden.
2. Fotografera en lapp eller ett A4-ark; tryck Skicka. Upprepa under samma femminuterslänk. Efter fem minuter kan kassan skapa en ny länk för samma köp.
3. I kassan visas alla bilder som miniatyrer. Välj en bild och klicka AI-avläsning. Nya förslag **läggs till** befintliga varor och är alltid osäkra tills manuellt granskade. En bild kan inte AI-läsas två gånger i samma webbläsarutkast.
4. Granska alla varor och genomför en enda betalning. Varje originalbild sparas separat i serverns bildlager under köpets session.

## Viktiga begränsningar

* Bildöversikten är en samling originalbilder, **inte** en exporterad sammansatt kollagefil.
* Koppling mellan varurad och `photoId` sparas i kassans lokala utkast men ännu inte i `sale_items`-tabellen.
* Mobilens uppladdningslänk är återanvändbar i fem minuter och ska inte delas med obehöriga.
* För att undvika dubbelräkning måste personalen kontrollera att varje bild bara läses en gång.
* Efter omladdning kan foton visas igen via sessionen; kontrollera raderna innan betalning.
