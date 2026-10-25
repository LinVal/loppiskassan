# Loppiskassan v8 – nätverksavbrott och återförsök

Två nya regressionstester i `tests/test_network_retries.py`:

1. Om servern sparar köpet men kassans svar försvinner, ska ett nytt anrop
   med samma sessions-ID returnera samma försäljnings-ID och inte skapa en dubblett.
2. Sex upprepade anrop till samma session ska bara spara två varurader en gång.

Kör med `pytest -q` eller låt GitHub Actions köra automatiskt.

**Begränsning:** Detta är simuleringar av förlorade HTTP-svar, inte verkliga
nätverksavbrott eller processkrascher. Försäljningen är för närvarande
idempotent per sessions-ID, inte per godtycklig klientnyckel. Om kassan
skapar en ny session efter ett avbrott finns fortfarande risk för dubblett.
Det bör lösas i nästa implementation tillsammans med UI-återhämtning.
