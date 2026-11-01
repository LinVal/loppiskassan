# QR-skanning i Loppiskassan

## Användning
1. Öppna **Skarpt läge → Kassan → 1. Skanna varor**.
2. Tryck **Skanna med mobilen** och öppna kopplings-QR-koden med telefonen.
3. I mobilvyn: välj **Starta QR-kamera**, rikta mot en av de 12 testlapparna i `testlappar_qr.pdf`.
4. QR-varan skickas till pågående köp och visas i steg 2 för manuell granskning.
5. Alternativt: fotografera handskrivna lappar som tidigare. Båda metoderna fungerar i samma köp.

## Viktigt
- Varukoder har formatet `LK1|säljnummer|pris|beskrivning`. Säljnummer 1–250 och pris positivt och delbart med 5.
- Mobilkopplingens QR-kod är **inte** en varukod.
- Varje skanning skickas med unikt ID och servern förhindrar att samma ID registreras igen vid nätverksförsök. Att avsiktligt skanna samma fysiska QR-lapp två gånger kan däremot skapa två rader; kontrollera antalet innan betalning.
- Kameraavläsningen använder webbläsarens `BarcodeDetector`, som inte finns i alla mobilwebbläsare. Manuell inklistring av kodtext finns som reservväg. HTTPS och kameratillstånd krävs.
- QR-skanning är ingen betalning. Bekräfta varje rad i steg 2.
- Testlapparna är endast för test; genomför inte en riktig betalning för dem.
- De nya QR-skanningarna sparas i tabellen `qr_scans`.
- Mobilkoppling gäller fem minuter.

## Testa
Skanna minst två olika QR-lappar, fotografera sedan en vanlig lapp och kontrollera att allt hamnar i samma köp. Prova även felaktig kod, utgången mobilkoppling och nätverksavbrott.

## iPhone och Safari
Välj **Skanna QR med iPhone-kameran**, ta ett foto av en QR-testlapp och tryck **Läs QR från foto**. QR-koden läses på servern och skickas till samma köp. Det kräver inte BarcodeDetector i Safari. JPEG/PNG stöds, högst 6 MB. Direktkameran är endast ett alternativ för webbläsare med BarcodeDetector.

**Drift:** Den nya serveravläsningen kräver `opencv-python-headless` (ingår i requirements.txt). Kör tester och verifiera en riktig iPhone-fotografering efter deploy.
