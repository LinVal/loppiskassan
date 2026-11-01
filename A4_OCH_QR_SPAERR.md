# A4-kontrollark före betalning och QR-dubblettspärr

- Steg 2 innehåller **Visa / skriv ut A4-kontrollark**. Det skapas från aktuella varurader och är tydligt märkt **EJ BETALT / EJ BEKRÄFTAT**. Det sparar inte ett köp.
- QR-rader är gröna/verifierade (uncertain=false) efter servervalidering. AI-rader måste fortfarande granskas.
- Samma QR-innehåll (säljnummer, pris, beskrivning) får bara förekomma en gång per serverköp, även om kameran läser koden igen långt senare. Servern har ett unikt databasindex.
- OBS: Två fysiskt olika lappar med exakt samma QR-innehåll betraktas som samma kod. För att tillåta identiska artiklar som separata exemplar behövs ett unikt artikel-ID i framtida QR-format.
- A4-arket återger QR-information i text och eventuella originalfoton för AI/manuella varor. Det återger inte en grafisk QR-symbol; sådan kräver ytterligare arbete.
- A4-arket är ett tillfälligt förhandsunderlag i webbläsaren, inte ännu ett permanent arkivobjekt i Bucketeer.
- Testa särskilt med en ny köpsession, en QR-lapp skannad två gånger, samt en AI-lapp. Kontrollera ark före betalning.
