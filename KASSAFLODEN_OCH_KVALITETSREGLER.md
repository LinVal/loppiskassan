# Loppiskassan – kassaflöden och kvalitetsregler

**Version:** Betalningsflöde 2.0 · **Målgrupp:** kassapersonal, ansvariga, utvecklare och testare.

## 1. Syfte och grundprinciper
Loppiskassan registrerar försäljning av varor som tillhör olika säljare vid samma loppis. En kund kan köpa flera varor från flera säljare. Försäljningen fördelas på säljarna; betalningen tas emot av arrangörens kassor. Varje köp har **exakt ett betalsätt**: Swish, kort eller kontant. Blandade betalningar stöds inte.

**Viktigt:** Swish och kort verifieras **inte automatiskt**. Kassapersonalens bekräftelse betyder att personalen har sett betalningen i mottagarens app eller terminal. För kontanter måste personalen fysiskt ha tagit emot pengarna.

## 2. Normalflöde – från ny kund till avslutat köp

| Steg | Personalens handling | Systemets kontroll | Resultat |
|---|---|---|---|
| 0. Demonstration | Öppnar kassan | Exempelköp visas, men kan inte sparas på servern | Trygg introduktion |
| 1. Starta köp | Klickar **Starta serverköp** | Skapar unikt sessions-ID; rensar exempelbild och exempelvaror | Aktivt köp |
| 2. Registrera | Skannar via mobil och AI eller lägger till manuellt | AI-resultat är förslag och måste granskas | Varulista |
| 3. Kontrollera | Jämför varor, säljarnummer, priser och antal mot A4-arket | Pris måste vara positivt heltal delbart med 5; osäkra AI-rader kräver kontroll | Granskad varulista |
| 4. Betalning | Väljer ett betalsätt, anger mottagare, tar betalt | Kontanter: mottaget belopp måste täcka totalsumman | Manuell betalningsbekräftelse |
| 5. Slutgranskning | Ser totalsumma, antal varor, betalsätt och mottagare | Systemet tar en ögonblicksbild av varor och betalningsuppgifter | Bekräftelsedialog |
| 6. Spara | Klickar **Spara köp på servern** | Avvisar ändringar efter slutgranskning; samma sessions-ID kan bara skapa en försäljning | Sparad försäljning |
| 7. Nästa kund | Klickar **Nästa kund** | Ny session, tom varulista och tom bildyta | Nytt köp |

### Betalsätt
- **Swish:** personalen ser mottagen betalning hos rätt mottagare och bekräftar manuellt. Ange mottagaren, exempelvis kassans Swish-konto. Ett gemensamt Swish-nummer kan införas senare utan att byta betalsätt.
- **Kort:** personalen slår in beloppet i en fristående terminal, ser ett godkännande och bekräftar manuellt. Loppiskassan styr inte kortterminalen.
- **Kontant:** personalen anger mottaget belopp. Systemet visar växel; belopp under totalsumman blockeras även av servern. Registreringen av mottaget belopp används för kontroll i detta flöde, men **sparas ännu inte som separat kassatransaktion**.

## 3. Kvalitetsregler

| ID | Regel | Var kontrolleras den? | Om regeln bryts |
|---|---|---|---|
| K01 | Serverköp krävs för riktig försäljning | Kassan och servern | Exempelköp kan inte sparas |
| K02 | Minst en vara krävs | Kassan och servern | Stopp |
| K03 | Säljarnummer ska bestå av 1–4 siffror | Kassan och servern | Stopp |
| K04 | Pris ska vara 5, 10, 15, 20 … kr | Kassan och servern | Omedelbart fel i fältet och stopp |
| K05 | AI-osäkra lappar ska granskas | Kassan | Stopp innan betalning |
| K06 | Betalningen måste bekräftas av personal | Kassan och servern | Stopp |
| K07 | Endast Swish, Kort eller Kontant | Kassan och servern | Stopp |
| K08 | Kontantbelopp ska vara heltal ≥ totalsumman | Kassan och servern | Stopp |
| K09 | Varor och betalningsuppgifter får inte ändras efter slutgranskning utan ny granskning | Kassan | Ny granskning krävs |
| K10 | En session får högst en sparad försäljning | Servern, unik databaskoppling | Befintlig försäljning returneras |
| K11 | Vid osäker nätverksstatus används samma sessions-ID | Kassan | Kontrollera status; skapa inte nytt köp |

### Viktiga avgränsningar
- **Säljarens existens i rätt evenemang är ännu inte garanterad av kassans slutgranskning.** Säljar-ID kontrolleras i nuläget framför allt avseende format. Detta är en planerad kvalitetsförbättring.
- **Betalningens verkliga status är inte maskinellt verifierad.** Manuell bekräftelse kan vara felaktig och behöver kompletteras med avstämning.
- **Varulistan låses logiskt vid slutgranskningen** genom att en ändring blockerar sparandet; detta är inte ett separat beständigt betalningstillstånd i databasen.
- Kontantkassa, ingående växel, uttag, återbetalningar och dagsavstämning **är ännu inte färdigbyggda**.
- Den befintliga databasen sparar betalsätt, mottagare, kassa och totalbelopp. Kontant mottaget belopp och växel sparas inte separat.

## 4. Fel- och avbrottsflöden

**Fel pris:** Prisfältet markeras. Rätta till ett positivt heltal delbart med 5; avrunda aldrig automatiskt.

**AI läser fel eller missar lapp:** Jämför alltid bild och antal fysiska lappar. Rätta säljar-ID/pris, komplettera saknade lappar, markera osäkra lappar kontrollerade först efter granskning.

**Kunden ångrar en vara:** Ta bort varan före betalningsbekräftelse och gör om slutgranskningen. Om betalning redan genomförts krävs manuell hantering; återbetalningsflöde är inte implementerat.

**Kort nekas / Swish uteblir:** Bekräfta inte betalningen. Behåll köpet och försök med valt eller nytt betalsätt; endast ett betalsätt får slutligen registreras.

**Kontanter räcker inte:** Avsluta inte köpet. Ange nytt mottaget belopp eller byt betalsätt.

**Internet försvinner före sparande:** Påbörjat köp återställs från webbläsarens lokala lagring när det går. Betalning och försäljning är inte registrerade automatiskt.

**Internet försvinner efter betalning eller under sparande:** Ta inte betalt igen. Kassan kontrollerar först om sessionen redan är sparad; använd samma session vid återförsök. Kontakta ansvarig om status är oklar.

**Dubbelklick:** Kassan blockerar parallella sparförsök. Serverns unika sessions-ID förhindrar dubbel försäljning.

**Flera kassor:** Varje köp har separat sessions-ID och kassanummer. Samma säljare kan förekomma i flera köp. Samtidighet ska även verifieras i PostgreSQL-tester.

## 5. Förslag på acceptanstester inför skarp drift
1. Normal Swish-försäljning med 15 varor från 7 säljare.
2. Kortbetalning: terminalen godkänner, personalen bekräftar, köp sparas en gång.
3. Kontant 185 kr, mottaget 200 kr → 15 kr växel; 180 kr blockeras.
4. Ändra en varas pris efter att bekräftelsedialogen öppnats → sparandet ska stoppas.
5. AI läser 12 kr → priset markeras som fel; 15 kr accepteras.
6. Avbruten betalning → ingen försäljning sparas.
7. Tappa nätet vid sparande, försök igen → högst en försäljning.
8. Starta nästa kund → inga gamla varor eller foton följer med.
9. Två kassor registrerar varor för samma säljare samtidigt.
10. Avstäm mot verkliga Swish-/kortbetalningar och kontanter vid dagens slut (manuell rutin tills rapportstöd byggts).

## 6. Roller och ansvar
**Kassapersonal:** kontrollerar varor, betalningsmottagare, faktiskt mottagen betalning och eventuella avbrott. **Arrangör/administratör:** ansvarar för Swish-/kortavtal, kontanthantering, avstämning, rättelser och säljaravräkning. **Systemet:** registrerar, validerar och förhindrar dubbelsparande per session – men ersätter inte betalningskontrollen.

## 7. Nästa förbättringar
1. Verifiera att säljaren finns och är aktiv i aktuellt evenemang.
2. Inför explicit status för betalning och sparande i serverns datamodell, med spårbar personalidentitet.
3. Kontantjournal och avstämning per kassa, inklusive växelkassa, uttag och återbetalningar.
4. Gemensamt Swish-nummer, referens på köp och eventuell framtida automatisk betalningsverifiering.
5. Integrerad kortbetalning först om leverantör, API och avtal stödjer det.

## 8. Enkel förklaring att ge kassapersonal
**Starta köp → registrera alla lappar → kontrollera säljare och pris → välj ett betalsätt → kontrollera att betalningen faktiskt kommit fram → granska sammanställningen → spara → nästa kund.** Om nätverket krånglar: **ta inte betalt en gång till och starta inte nytt köp innan statusen är klar.**
