# Samlade förbättringar – 1 november 2026

## 1. Originalfoto och AI-spårbarhet
Vid serverförsäljning kan varje varurad skicka `photo_id`, ursprungligt AI-förslag för säljnummer/pris/beskrivning och AI-osäkerhet. Servern verifierar att fotot hör till samma köpsession, och lagrar uppgifterna i en separat `item_evidence`-tabell. Administrativ köphistorik returnerar dessa fält. Äldre varurader saknar dem (null). Manuell vara utan foto stöds.

## 2. Personalkonton och behörighet
Servern kontrollerar administrativa API-anrop för historik, rapporter, event och avstämning. En administratör kan skapa och spärra personal via **Personal & kassor**. Endpoint `/api/staff/me` ger den autentiserade rollen. Observera att rollväljaren i vänstermenyn fortfarande är ett visuellt filter: den kan **inte** ge fler rättigheter än inloggat konto. HTTP Basic är fortfarande befintlig autentiseringsmetod. Konton behöver skapas av admin innan användning.

## 3. Manuell kassaavstämning
Under **Betalningar** visas totalsummor per kassa och betalsätt för ett angivet evenemangs-ID. Administratören kan registrera räknat belopp och en notering; systemet beräknar differens och sparar tid och användare. Detta är **inte** en verifiering mot Swish/kortleverantör eller faktisk bankinsättning. Avstämningar sparas utan att ändra försäljningarna.

## 4. Mobilskanning
Mobilvyn har nu en tydlig knapp **Skanna nästa lapp** och en räknare för skickade bilder. Bilden kan skickas och nästa fotograferas utan att lämna köpet. Den tidsbegränsade länken och befintlig servervalidering finns kvar.

## 5. Historik för kassapersonal
Steg 4 i den skarpa kassan kan visa de senaste serverregistrerade köpen för vald kassa, med tid, betalsätt och belopp. Inga övningsköp visas där. Denna funktion visar **inte** fullständiga varurader eller originalbilder; dessa finns i adminhistoriken.

## 6. Felhantering
Kassan ger tydligare text när kontakten med servern bryts och behåller köputkastet för återförsök. AI-fel har redan separat feltext och manuell inmatning. Ytterligare end-to-end-nätverksprov bör göras på mobil.

## Begränsningar och driftsättning
- `item_evidence` och `register_reconciliations` skapas automatiskt när appen startar. Säkerhetskopiera databasen före deploy.
- Kontrollera ett fullständigt köp i staging, särskilt foto → AI → rättning → betalning → köphistorik.
- Kör GitHub Actions PostgreSQL-belastningstest; lokalt hoppas det över utan testdatabas.
- Den tidigare fyrastegs-kassan, rosa bakgrund och separata demoläget är bevarade.
- Ingen automatisk kontantkassa, betalningsintegration eller exporterat bildkollage ingår.
