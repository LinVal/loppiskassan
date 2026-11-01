Korrigering 2026-11-01

1. Tog bort en äldre, dubblerad startQR-klickhanterare som skrev över Safari-flödet och krävde BarcodeDetector.
2. Monterade /static i FastAPI så /static/design-system.css inte längre ger 404.
3. Mobilens QR-skanner använder getUserMedia och skickar videobildrutor för serveravkodning.

Verifiera på iPhone efter deploy: ny mobilkoppling, starta QR-skanning, kameraåtkomst, testlapp.
