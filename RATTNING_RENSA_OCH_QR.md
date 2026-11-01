# Rättning: rensning och QR-feedback

- **Rensa varulista** avbryter nu serverköpet, ogiltigförklarar mobilkopplingen och tar bort lokalt utkast. Gamla QR-skanningar kan inte hämtas tillbaka efter omladdning. Historiska foton raderas inte från lagringen automatiskt.
- Vid serverfel rensas inget lokalt, så att köpet inte hamnar i osynk.
- Grön QR-bekräftelse får ligga kvar under pågående skanning av samma kod i minst åtta sekunder i stället för att omedelbart ersättas av gul dubblettvarning. Om samma kod skannas igen senare visas gul varning; ingen dubblett sparas.
- Starta ny mobilkoppling efter rensning.
