# eScraper

Lokales Entscheidungstool für den An- und Weiterverkauf gebrauchter Gaming-PC-Komponenten in Deutschland.

eScraper beantwortet fünf Fragen zu einem Angebot:

1. Welches Bauteil oder welches Bundle wird angeboten?
2. In welcher konservativen Preisspanne lässt sich es heute weiterverkaufen?
3. Welcher Deckungsbeitrag bleibt nach Gebühren, Versand, Arbeit, Risiko und Steuer-Schätzung?
4. Was ist der höchste wirtschaftlich vertretbare Einkaufspreis?
5. Warum empfiehlt das System `BUY`, `NEGOTIATE`, `WATCH` oder `REJECT`?

Die Anwendung kauft nichts, schreibt keine Verkäufer an, gibt keine Gebote ab, veröffentlicht keine Verkaufsanzeigen und ersetzt keine Steuer- oder Rechtsberatung.

## Aktueller Stand

Das Repository enthält die **lokale Foundation** (Slice 1): FastAPI-Backend, Health-API, Docker-Compose für PostgreSQL und Redis sowie die ersten Domänen-Typen (Geld in Cent, Enums).

Noch **nicht** enthalten und daher unten als geplant markiert:

- React-Dashboard
- Datenbankschema und Alembic-Migrationen
- eBay-Browse-API, Watchlists und Worker
- Bewertungs-, Markt- und Finanzlogik
- CSV-/Product-Research-Import
- Kleinanzeigen-Companion-Erweiterung
- Inventar und Testdokumentation
- Demo-Daten und Live-eBay-Check

Die Bedienung in den späteren Abschnitten beschreibt das **Zielprodukt** aus der genehmigten Spezifikation. Befehle ohne den Hinweis *geplant* funktionieren mit dem aktuellen Code.

Spezifikation: [`docs/superpowers/specs/2026-08-27-pc-hardware-flipping-dashboard-design.md`](docs/superpowers/specs/2026-08-27-pc-hardware-flipping-dashboard-design.md)

---

## Architektur

```text
React-Dashboard                         (geplant)
      |
Versionierte FastAPI-HTTP-API           (GET /api/v1/health vorhanden)
      |
      +-- Quellenadapter                (geplant)
      |     +-- eBay Browse API
      |     +-- bestätigter Companion-Import
      |     +-- CSV / manuelle Comparables
      |
      +-- Produktnormalisierung         (geplant)
      +-- Marktschätzung                (geplant)
      +-- Finanzbewertung               (geplant)
      +-- Risiko und Empfehlung         (geplant)
      +-- Inventar und Testläufe        (geplant)
      |
PostgreSQL                              (Compose vorhanden, Schema geplant)
      |
Redis-Queue <--> Python-Worker          (Redis vorhanden, Worker geplant)
```

Der Stack ist **local-first** und für **einen Nutzer**. Dienste binden an `127.0.0.1`. Öffentliches Hosting, Mehrbenutzerbetrieb und mobile Apps gehören nicht zum MVP.

Geldbeträge werden intern als **ganze Cent** gespeichert, Prozentsätze als **Basispunkte** (100 bp = 1 %). Zeitstempel sind UTC, Primärschlüssel UUIDs. Marktplatz und Währung sind explizit; zunächst `EBAY_DE`, `KLEINANZEIGEN_DE` und `EUR`.

---

## Voraussetzungen

| Software | Zweck |
| --- | --- |
| Docker Desktop inkl. Compose | PostgreSQL, Redis und Backend lokal starten |
| Python 3.13 | Backend-Entwicklung und Tests (nicht 3.12 oder 3.15) |
| Git | Repository klonen |

Später zusätzlich:

| Software | Zweck |
| --- | --- |
| Node.js (LTS) | Frontend und Browser-Erweiterung bauen (*geplant*) |
| eBay-Developer-Account | Browse-API für aktive Angebote (*geplant*) |
| Chromium/Chrome | Companion-Erweiterung laden (*geplant*) |

eBay-Zugangsdaten sind für den Health-Check und die Unit-Tests **nicht** nötig.

---

## Setup

### 1. Repository und Umgebungsdatei

Im Projektroot:

```powershell
Copy-Item .env.example .env
```

`.env` bleibt lokal und ist gitignored. Trage später echte eBay-Werte nur dort ein, niemals in `.env.example`.

### 2. Stack mit Docker starten

```powershell
docker compose up -d --build
```

Aktuell startet Compose:

| Dienst | Adresse | Rolle |
| --- | --- | --- |
| `postgres` | intern `postgres:5432` | System of Record |
| `redis` | intern `redis:6379` | Queue / Cache |
| `backend` | [http://127.0.0.1:8000](http://127.0.0.1:8000) | FastAPI |

Prüfen:

```powershell
docker compose ps
curl http://127.0.0.1:8000/api/v1/health
```

Erwartete Antwort:

```json
{"status":"ok"}
```

OpenAPI-UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Stoppen:

```powershell
docker compose down
```

Daten in den Volumes `postgres_data` und `redis_data` bleiben erhalten. Vollständiges Zurücksetzen:

```powershell
docker compose down -v
```

### 3. Backend lokal ohne Docker (Entwicklung)

PostgreSQL und Redis können weiter in Compose laufen. Die `.env.example` nutzt die Hostnamen `postgres` und `redis` im Compose-Netz. Für uvicorn auf dem Host die URLs auf `localhost` umbiegen:

```env
DATABASE_URL=postgresql+asyncpg://escraper:escraper@localhost:5432/escraper
REDIS_URL=redis://localhost:6379/0
FRONTEND_ORIGIN=http://localhost:5173
```

Dazu die Datenbank und Redis nach außen freigeben (aktuell nicht in `compose.yaml` gemappt) oder nur Tests ohne laufende Datenbank ausführen. Die vorhandenen Health- und Domänentests brauchen keine Datenbank.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

---

## Konfiguration

| Variable | Bedeutung |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy-URL mit `postgresql+asyncpg` |
| `REDIS_URL` | Redis für die geplante Job-Queue |
| `FRONTEND_ORIGIN` | Erlaubte CORS-Origin des Dashboards, Standard `http://localhost:5173` |
| `LOG_LEVEL` | Log-Stufe, Standard `INFO` |
| `EBAY_CLIENT_ID` | eBay-App-Client-ID (*geplant*, leer lassen bis die Integration existiert) |
| `EBAY_CLIENT_SECRET` | eBay-App-Secret (*geplant*, niemals committen) |
| `EBAY_MARKETPLACE_ID` | Marktplatz, Standard `EBAY_DE` |

CORS erlaubt nur die konfigurierte Frontend-Origin. Das Header `X-Extension-Token` ist für die spätere Companion-Kopplung vorgesehen.

Secrets gehören ausschließlich in `.env`. Die API gibt sie nicht zurück, und sie dürfen nicht in Logs, Fixtures, Screenshots oder Commits erscheinen.

---

## Datenbank-Migrationen

*Geplant.* Schemaänderungen laufen ausschließlich über Alembic.

Vorgesehene Befehle nach Einführung der Migrationen:

```powershell
docker compose exec backend alembic upgrade head
docker compose exec backend alembic current
```

Manuelle SQL-Änderungen an der laufenden Datenbank sind nicht vorgesehen.

---

## So verwendest du eScraper

Dieser Abschnitt ist der Betriebsablauf des fertigen MVP. Schritte mit *geplant* sind im aktuellen Code noch nicht ausführbar.

### Arbeitsmodell

eScraper ist ein **Bewertungswerkzeug**, kein Autopilot:

- Du definierst, wonach gesucht wird (Watchlists, CSV, manuelle Comparables, einzelne Kleinanzeigen).
- Das System normalisiert das Angebot, schätzt konservative Wiederverkaufswerte und rechnet Kosten, Arbeit, Risiko und Steuer-Schätzung durch.
- Du entscheidest. Das System kauft, bietet und schreibt nicht.

Aktive eBay-Angebote sind **Angebotspreise**. Realisierte Verkaufspreise kommen nur aus Daten, die du selbst und berechtigt importierst (z. B. eBay Product Research als CSV oder manuelle Eingabe).

### Typischer Tagesablauf (*geplant*)

1. Stack starten (`docker compose up -d`).
2. Dashboard öffnen (`http://localhost:5173`).
3. Overview auf Quellenstatus, fehlgeschlagene Jobs und Review-Warteschlange prüfen.
4. Watchlists laufen lassen bzw. neue Comparables importieren.
5. Deals nach Empfehlung, Gewinn, ROI und Kapitalbedarf filtern.
6. Deal-Detail lesen: Produktmatch, Comparables, Kostenzerlegung, Maximalpreis, Gründe.
7. Bei Bedarf Kleinanzeigen-Listing per Companion importieren (ein Tab, ein Klick, Vorschau bestätigen).
8. Gekaufte Teile ins Inventar legen und Tests dokumentieren.
9. Cost-Profile und Risikoregeln nur versioniert ändern; alte Bewertungen bleiben nachvollziehbar.

### 1. Übersicht (Overview)

Zeigt neue `BUY`-Kandidaten, die besten Verhandlungschancen, benötigtes Kapital, veraltete Marktdaten, fehlgeschlagene Jobs und den Gesundheitszustand der Quellen.

Wenn eine Quelle ausgefallen ist, bleibt der letzte erfolgreiche Datenstand sichtbar, aber mit klarem Altersstempel. Veraltete Schätzungen dürfen höchstens `WATCH` ergeben.

### 2. Watchlists für eBay

Eine Watchlist beschreibt, welche aktiven Angebote die Browse-API holen soll:

- Produktmodell bzw. Suchbegriffe
- Einschluss- und Ausschlusswörter
- Kategorie und Zustand
- Preisobergrenze
- Standortfilter
- Abfrageintervall (begrenzt durch eBay-Kontingente)
- Alert-Verhalten

Der Worker pollt nur konfigurierte Watchlists. Neue oder geänderte Listings werden als unveränderliche Rohbeobachtung gespeichert. Eine neue Observation entsteht nur, wenn sich relevante Felder ändern.

Ohne gültige eBay-Credentials bleibt der Live-Check offen; Fixture-Tests ersetzen keinen echten API-Aufruf.

### 3. Marktdaten und Comparables

Unter **Market data** siehst du je Produkt:

- Downside-Preis (25. Perzentil, schnelle Veräußerung)
- Erwartungswert (gewichteter Median)
- Oberes Perzentil (informativ, **nie** Grundlage für den Maximal-Einkaufspreis)
- Anzahl Comparables, Datenalter, aktives Angebot, Liquidität

**Wichtig:** Aktive Asks belegen keinen realisierten Preis. Verkaufte Comparables kommen nur aus autorisiertem manuellen oder CSV-Import (z. B. aus eBay Product Research).

CSV-Felder (Vorschau und Validierung vor dem Speichern):

- kanonisches Produkt oder Identifikatoren
- Zustand
- Marktplatz
- Verkaufsdatum oder Aggregat-Zeitraum
- realisierter Artikelpreis
- realisierter Versand
- Beobachtungsanzahl bei Aggregaten
- Verkaufsrate, falls vorhanden
- Quellennotiz

Ungültige Währung, unklare Produktzuordnung, unmögliche Daten oder fehlende realisierte Preise werden zeilenweise abgelehnt. Gültige Zeilen bleiben erhalten.

### 4. Deals bewerten

Die Deals-Liste filtert und sortiert nach Empfehlung, Kategorie, erwartetem Gewinn, ROI, Score, Quelle, Konfidenz, Standort, Alter und Kapitalbedarf.

Im Deal-Detail stehen:

- Originallink und erfasste Rohwerte
- kanonisches Produkt und Match-Konfidenz
- Comparable-Verteilung und Herkunft (Ask vs. Sale getrennt)
- vollständige Kosten- und Reservezerlegung
- maximaler Einkaufspreis
- Regel-Erklärungen
- Bewertungshistorie
- eigene Entscheidung und Notizen

Empfehlungen:

| Empfehlung | Bedeutung |
| --- | --- |
| `BUY` | Alle harten Gates am aktuellen Landed-Cost bestehen. |
| `NEGOTIATE` | Das Angebot würde am oder unter dem berechneten Maximalpreis bestehen. |
| `WATCH` | Daten unzureichend oder veraltet, aber kein blockierender Mangel. |
| `REJECT` | Blockierendes Risiko oder kein nicht-negativer tragfähiger Einkaufspreis. |

`BUY` ist ausgeschlossen, wenn eines gilt:

- Downside-Gewinn unter dem konfigurierten Minimum
- erwarteter Gewinn oder ROI unter dem Minimum
- Produkt oder Variante unklar
- Marktdaten-Konfidenz niedrig
- blockierende Risikoregel ohne erforderliche Evidenz
- aktueller Landed-Cost über dem Maximalpreis

Mehrdeutige Varianten (z. B. RTX 3060 8 GB vs. 12 GB, 5600 vs. 5600X) dürfen kein `BUY` erhalten. Eine Nutzerkorrektur legt einen Alias an, überschreibt aber nicht das Original-Listing.

### 5. Kleinanzeigen per Companion

Kein Crawler. Die Erweiterung:

- läuft nur im vom Nutzer geöffneten aktiven Tab
- startet nur nach explizitem Klick
- navigiert, paginiert, pollt und loggt nicht ein
- löst keine CAPTCHAs und umgeht keine Zugangsbeschränkungen
- überträgt nur Minimalfelder (URL, externe ID falls sichtbar, Titel, Preis, Zustandstext, Ort, Versand/Abholung, ausgewählter Beschreibungstext, Capture-Zeit)
- zeigt eine Vorschau, die du bestätigst oder editierst
- sendet nur an das gekoppelte lokale Backend
- kopiert keine Verkäuferkontakte und keine Bilder

Ohne dokumentierte schriftliche Erlaubnis von Kleinanzeigen bleibt automatisiertes Playwright-Sammeln abwesend und deaktiviert.

### 6. Inventar und Tests

Gekaufte Hardware wird mit Anschaffungskosten, Seriennummer, Zustand, Aufbereitung, Testdurchgängen, Evidenzdateien und späterem Verkaufsergebnis geführt.

Ein Testlauf speichert Verfahren, Werkzeug, Dauer, Konfiguration, Ergebnis, Messwerte und Notizen. Das MVP **zeichnet** Tests auf; es führt keine Benchmarks automatisch aus.

### 7. Einstellungen

Hier pflegst du:

- Cost-Profile (Gebühren, Versand, Verpackung, Anfahrt, Aufbereitung, Stundensatz, Mindestgewinn, Mindest-ROI, Risiko-Reserven, Steuer-Schätzprofil)
- Score-Ziele
- Risikoregeln (effektiv datiert, editierbar)
- Quellenstatus und Extension-Pairing
- Importe und Aufbewahrung

Profile und Regeln sind versionsbehaftet. Eine neue Bewertung speichert, welche Versionen sie verwendet hat. Alte Snapshots werden nicht überschrieben.

Steuerprofile: privat, Kleinunternehmer, Regelbesteuerung, Differenzbesteuerung nach § 25a UStG. Letzteres nur, wenn der Einkauf eine kompatible Lieferanten-Steuerklassifikation hat. Jedes Steuerergebnis ist eine **Schätzung**.

---

## Berechnungsmodell (*geplant*)

```text
Verkaufserlöse
- Einkaufspreis
- Plattform- und Zahlungsgebühren
- Ausgangsversand und Verpackung
- Aufbereitungsteile
- Anfahrt
- bewertete Arbeit
- Inserats- und Werbekosten
- geschätzte Steuer
- erwartete Reserve für Retouren, Defekte und Betrug
= erwarteter Deckungsbeitrag
```

Der Maximal-Einkaufspreis ist der höchste Preis, bei dem **alle** konfigurierten Gates mit dem **Downside**-Wiederverkaufswert noch halten. Gebühren und Steuer-Schätzung können vom Betrag abhängen, daher wird das komplette Modell gelöst.

Startwerte (konfigurierbar):

- Mindest-Deckungsbeitrag erwartet: 15,00 EUR
- Mindest-ROI erwartet: 15 %
- Mindest-Downside-Deckungsbeitrag: 0,00 EUR

Ranking-Score (rangiert Kandidaten, überschreibt keine Gates):

- 35 % erwarteter absoluter Deckungsbeitrag
- 20 % erwarteter ROI
- 15 % Liquidität
- 15 % Comparable-Konfidenz
- 15 % inverses erwartetes Risiko

Komplette PCs können als Ganzes oder als Part-out bewertet werden. Jede identifizierte Komponente gehört genau einem Szenario. Unbekannte Teile zählen 0, bis sie reviewed sind. Die Empfehlung zeigt beide Szenarien und wählt die konservativere bestehende Option.

Konfidenz:

- Hoch: mindestens 20 exakte Sold-Comparables in 90 Tagen
- Mittel: mindestens 8 in 180 Tagen
- Niedrig: darunter, nur verwandte Varianten oder nur aktive Asks → Empfehlung höchstens `WATCH`

---

## Demo-Daten

*Geplant.* Nach Migrationen:

```powershell
docker compose exec backend python scripts/seed_demo.py
```

Vorgesehener Seed: Katalogprodukte, ein Small-Business-Cost-Profile, initiale Risikoregeln, 20 Sold-Comparables für RTX 3060 12 GB, ein aktives eBay-Angebot, ein mehrdeutiges Review-Item, ein fehlgeschlagener Job, ein Inventar-Artikel mit Testevidenz.

---

## Tests

Aktuell (Backend-Foundation):

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
ruff check app tests
pytest -v
```

Abgedeckt sind `GET /api/v1/health`, Cent-Arithmetik / Basispunkte und stabile Enum-Werte.

Vollständige Matrix (*geplant*):

```powershell
cd backend
ruff check app tests scripts
pytest -v
cd ..\frontend
npm test
npm run build
npm run e2e
cd ..\extension
npm test
npm run build
```

Live-eBay-Aufrufe sind getrennte Acceptance-Checks und gelten nicht als bestanden, nur weil Fixture-Tests grün sind.

---

## eBay Live Check

*Geplant.*

```powershell
docker compose exec backend python scripts/verify_ebay.py
```

Das Skript gibt nur den Zustand der Credentials aus, nie die Werte:

```text
EBAY_CLIENT_ID=SET|EMPTY|MISSING
EBAY_CLIENT_SECRET=SET|EMPTY|MISSING
```

| Exit | Bedeutung |
| --- | --- |
| 0 | `LIVE_EBAY=PASS count=<n>` – Credentials gesetzt und ein echter Browse-Aufruf erfolgreich |
| 1 | `LIVE_EBAY=FAIL code=<typed-code>` – Aufruf fehlgeschlagen |
| 2 | `LIVE_EBAY=OPEN` – Credentials nicht gesetzt |

Request-Header und Response-Bodies werden nicht ausgegeben.

---

## Companion-Installation

*Geplant.* Nach dem Build der Erweiterung:

```powershell
cd extension
npm test
npm run build
```

In Chromium/Chrome:

1. `chrome://extensions` öffnen
2. Entwicklermodus einschalten
3. Entpackte Erweiterung laden (Build-Verzeichnis)
4. Mit dem lokalen Backend koppeln (kurzlebiger Token, nur localhost)
5. Eine Kleinanzeigen-Seite manuell öffnen, Erweiterung klicken, Vorschau prüfen, bestätigen

Die Erweiterung darf nicht im Hintergrund Seiten laden.

---

## Kleinanzeigen-Grenze

Kleinanzeigen untersagt automatisierte Crawler und Datensammlung ohne ausdrückliche schriftliche Zustimmung. Die Wahl des Tools ändert diese Grenze nicht.

Erlaubt im MVP: einmaliger, nutzerausgelöster Import der aktuell offenen Anzeige nach Bestätigung.

Nicht erlaubt und im MVP nicht vorhanden:

- automatisches Durchsuchen, Paginieren, Polling, Refresh oder Scheduling
- Login-Automatisierung, CAPTCHA-Lösung, Anti-Bot-Bypass
- Sammeln von Verkäuferkontakten
- Kopieren von Bildern
- automatisches Kaufen, Bieten, Verhandeln oder Nachrichten

---

## Credential-Sicherheit

- eBay-Secrets nur in ignorierter lokaler `.env`
- niemals in API-Antworten, Logs, Tests, Commits oder Screenshots
- Backend nur an `127.0.0.1:8000`
- CORS nur für die lokale Frontend-Origin
- Companion nur an allowlisted localhost
- importierter Text ist untrusted und darf nicht als HTML ausgeführt werden
- keine Verkäuferkontakte, keine Kleinanzeigen-Bilder

Öffentliches Deployment braucht ein eigenes Sicherheitsdesign (Auth, TLS, Autorisierung, Rate-Limits, Backups, Secret-Management) und ist nicht Teil dieses MVP.

---

## Backup

PostgreSQL-Daten liegen im Docker-Volume `postgres_data`.

Beispiel-Dump (*sobald das Schema existiert*):

```powershell
docker compose exec postgres pg_dump -U escraper escraper > backup.sql
```

`.env` separat und außerhalb des Repos sichern. Redis enthält Queue-Zustand, nicht die System-of-Record-Wahrheit.

---

## Troubleshooting

| Symptom | Prüfung |
| --- | --- |
| `curl` auf `/api/v1/health` schlägt fehl | `docker compose ps` – `backend` healthy? Port 8000 belegt? |
| Backend startet nicht | `docker compose logs backend` – `.env` vorhanden? `DATABASE_URL` zeigt im Container auf Host `postgres`? |
| Postgres unhealthy | `docker compose logs postgres` – Volume korrupt? `docker compose down -v` nur wenn Datenverlust akzeptabel |
| CORS-Fehler im Browser | `FRONTEND_ORIGIN` exakt wie die UI-URL, ohne trailing slash-Mismatch |
| eBay-Jobs fehlgeschlagen (*geplant*) | Quellenstatus im Dashboard; Quota und Auth nicht endlos retried; Credentials nie in Logs suchen |
| Empfehlung bleibt `WATCH` (*geplant*) | oft Absicht: niedrige Konfidenz, stale data oder unklare Variante |
| Python 3.12 / 3.14 | `requires-python = ">=3.13,<3.15"` – 3.13 verwenden |
| PowerShell blockiert venv | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |

---

## Verifikationsstatus

| Kriterium | Status |
| --- | --- |
| Compose startet Postgres, Redis und Backend | vorhanden |
| `GET /api/v1/health` liefert `{"status":"ok"}` | vorhanden |
| Geld in ganzen Cent, Basispunkte ganzzahlig | vorhanden |
| Stabile Enums (`EUR`, `EBAY_DE`, Empfehlungen, …) | vorhanden |
| Backend-Unit-Tests Health / Money / Enums | vorhanden |
| Alembic-Schema und persistente Listings | offen |
| Seeded Listing wird zu erklärbarer Bewertung | offen |
| Mehrdeutiges Produkt ohne `BUY` | offen |
| Niedrige/stale Konfidenz maximal `WATCH` | offen |
| Maximalpreis reagiert auf Kosten/ROI | offen |
| Part-out ohne Doppelzählung | offen |
| eBay-Credentials konfigurierbar, unsichtbar in UI/Logs | offen |
| Live-eBay-Acceptance | offen, bis Credentials + erfolgreicher Netzaufruf belegt sind |
| Companion importiert genau ein bestätigtes Listing | offen |
| Keine Live-Kleinanzeigen-Automatisierung | eingehalten (nicht implementiert) |
| Dashboard-Routen und Browser-Tests | offen |
| Worker, Frontend, Extension-Testsuiten | offen |

---

## Repository-Struktur

```text
eScraper/
├── backend/
│   ├── app/
│   │   ├── api/          # HTTP, derzeit Health
│   │   ├── core/         # Settings
│   │   └── domain/       # Money, Enums
│   ├── tests/
│   └── Dockerfile
├── docs/superpowers/
│   ├── specs/            # genehmigte Produktspezifikation
│   └── plans/            # Implementierungsplan
├── compose.yaml
├── .env.example
└── README.md
```

Geplant daneben: `frontend/`, `worker/`, `extension/`, `backend/migrations/`.

---

## Was bewusst nicht zum MVP gehört

- automatisierter Kleinanzeigen-Connector
- E-Mail-, Telegram- oder Push-Benachrichtigungen nach außen
- automatisches Veröffentlichen von eBay-Verkaufsanzeigen
- Mehrbenutzer und öffentliches Hosting
- automatische Hardware-Benchmarks
- ML-Preisprognose
- DATEV-/Buchhaltungs-Export
- automatisches Verhandeln oder Kaufen
