# Loppiskassan v6 – personalkonton och regressionstester

## Installera på befintlig Heroku-app

1. Säkerhetskopiera: `heroku pg:backups:capture -a loppiskassan`.
2. Behåll befintliga `DATABASE_URL`, Bucketeer, `OPENAI_API_KEY`, `PUBLIC_BASE_URL`, `DEMO_USER`, `DEMO_PASSWORD`.
3. Kör lokalt `pip install -r requirements.txt -r requirements-dev.txt && pytest -q`.
4. Uppdatera GitHub med filerna i detta paket. **Granska testerna innan driftsättning**. Heroku deployas först när du själv publicerar.
5. Vid första start skapas ett administratörskonto från `DEMO_USER` och `DEMO_PASSWORD`. Ändra sedan lösenordet via `POST /api/staff/change-password` med JSON `{"current_password":"...","new_password":"minst-12-tecken"}`. Att ändra `DEMO_PASSWORD` efter första starten ändrar **inte** kontots lösenord i databasen.
6. Öppna `/staff` som administratör och skapa ett konto per kassapersonal. Administratör använder `/admin` och `/events`.

## Regler

- Administratörer får hantera personal, säljare, provisioner, justeringar, avslut och utbetalningsmarkeringar.
- Kassapersonal får registrera köp, starta sessioner och hantera bild/AI-flödet. API:et kontrollerar roller, inte bara webbsidan.
- Användare lagras med saltade scrypt-hashar, och spärrade konton nekas direkt.
- Lyckade skrivande HTTP-anrop loggas med användarnamn, metod, sökväg, status och tid i `staff_audit`. Detta är en grundläggande åtgärdslogg, inte fullständig revisionshistorik över före/efter-värden.
- Ett köp per session; PostgreSQL-lås på sessionen hindrar samtidiga dubbla köp på samma session.
- Tio samtidiga separata kassor simuleras i automatiska tester med SQLite. **Detta ersätter inte ett riktigt belastningstest mot PostgreSQL**.
- Existerande v5-affärsregler och provisionstester ingår.

## GitHub Actions

`.github/workflows/tests.yml` kör pytest på push och pull request med en lokal, isolerad SQLite-databas. Det ansluter inte till din Heroku-databas. Aktivera branch protection och kräv den gröna `pytest`-kontrollen innan merge. Stäng av automatisk deploy från oskyddade grenar.

## Kända begränsningar före lansering

- Inloggning sker med HTTP Basic över HTTPS; det är en **utvecklingslösning**. Byt till sessionsbaserad autentisering med CSRF-skydd, sessionsutgång och säkert utloggningsflöde före skarp drift.
- Säljarportalen har privata länkar och mobiluppladdningen engångstoken; granska även dessa före lansering.
- Fullständig transaktions-/händelselogging, databas-migreringsverktyg, PostgreSQL-integrations- och stresstester samt backup-återställning återstår.
- Systemet är ännu inte säkerhetsgranskat eller godkänt för skarp drift.
