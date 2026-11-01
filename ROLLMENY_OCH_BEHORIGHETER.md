# Rollstyrd navigation – demonstration

## Syfte
En gemensam ingång `/app` för kassa och administration. En enkel rollväljare gör det möjligt att granska användarupplevelsen före riktig rollbaserad inloggning.

## Flöden
- **Kassapersonal:** välj Kassapersonal → endast Kassan syns → kassaflödet körs i samma huvudlayout.
- **Administratör:** välj Administratör → Kassan samt samtliga administrationsfunktioner syns.
- **Byte av läge:** välj annan roll i vänstermenyn; valet lagras i webbläsarens localStorage.
- **Direktlänk:** `/` fungerar fortfarande som tidigare, `/admin` och `/app` öppnar den gemensamma menyn.

## Säkerhetsregler och begränsningar
Rollväljaren är **inte autentisering eller auktorisation**. Alla kan välja Administratör i UI:t. Befintliga serverkontroller får inte tas bort och känsliga API-anrop måste kontrolleras på servern. Innan skarp rollstyrning ska `/app` hämta roll från inloggad session, och servern ska neka otillåtna API-anrop oberoende av synliga menyval.

## Kvalitetskontroller
- Kassaläget visar inte adminmenyer.
- Adminläget visar samtliga menyer och Kassan.
- Byte av roll påverkar inte pågående serverköp.
- Felaktig hash-adress ger första tillåtna vyn.
- Tidigare API-adresser och köpregler är oförändrade.
