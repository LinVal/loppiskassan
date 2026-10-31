# Evenemangsförberedelser och startkontroll

## Arbetsflöde för administratör

1. Skapa ett evenemang. Det får status **utkast**.
2. Välj utkastet i listan. Importera CSV, kopiera tidigare tilldelningar eller sök efter en permanent säljaridentitet och tilldela ett nummer.
3. Kontrollera sammanställningen: antal medarbetare, externa säljare, lediga nummer och eventuella startfel.
4. Filtrera tabellen på nummer, namn eller säljartyp. Frigör felaktiga nummer i utkastet och tilldela dem på nytt.
5. Kontrollera manuellt att **alla faktiskt anmälda säljare** finns med. Systemet kan inte veta vilka som borde ha anmält sig.
6. Starta evenemanget. Start kräver minst en tilldelad säljare, namn på samtliga tilldelningar och ingen personidentitet tilldelad flera nummer. Lediga nummer är tillåtna.

## Kvalitetsregler

- Säljnummer 1–250; ingen särskild nummergräns för medarbetare.
- Ett nummer kan bara vara tilldelat en säljare per evenemang.
- En permanent säljaridentitet får bara ha ett nummer i samma evenemang.
- Personer med samma namn sammanfogas aldrig automatiskt.
- Massimport och kopiering tillåts endast i utkast och stoppar vid konflikter.
- Frigöring av nummer tillåts endast i utkast.
- En startkontroll är **teknisk**, inte en garanti att den verkliga anmälningslistan är komplett.
- Försäljning kräver tilldelat nummer i ett öppet evenemang.

## Verifiering

API: `GET /api/v5/events/{id}/readiness` returnerar `ready`, `issues`, `assigned`, `staff`, `external` och `available`. Samma regler används vid start.

**Driftsättning:** Testa först i lokal miljö och i en testdatabas. Ingen migrering har körts på Heroku i denna leverans.
