# heise academy · Dialogstudio

Lokale Web-App für die Auswahl persönlicher LinkedIn-Beiträge und die Erstellung deutscher Kommentarentwürfe. Klare Trennung von Datenbeschaffung, Bewertung und Dashboard. **Kein Scraping, keine Browser-Bots, keine automatische Veröffentlichung.**

## Installation und Start

Voraussetzung: Python 3.12 oder neuer. Die Anwendung verwendet ausschließlich die Python-Standardbibliothek sowie natives HTML/CSS/JavaScript. Keine Paketinstallation, kein API-Key und kein Build erforderlich.

```bash
cd /workspace/heise-linkedin-automation
python3 -m app.server
```

Im eigenen Browser `http://127.0.0.1:8000` öffnen. Der Server bindet standardmäßig nur an Loopback. In einer Cloud-Umgebung den vorgesehenen Portzugang der Plattform verwenden. Mit Ctrl+C beenden.

Konfiguration erfolgt ausschließlich über Umgebungsvariablen:

| Variable | Standard | Zweck |
| --- | --- | --- |
| `HOST` | `127.0.0.1` | Bind-Adresse |
| `PORT` | `8000` | HTTP-Port |
| `APP_DB` | `.local/app.sqlite3` im Repository | SQLite-Datenbank für Imports, Entwürfe und Prüfstatus |

Beispiel: `PORT=8080 python3 -m app.server`. Die Datenbank wird automatisch angelegt, ist durch `.gitignore` ausgeschlossen und bleibt bei Neustarts erhalten. Sicherung: Server stoppen und die Datenbank kopieren. Kein Login oder Mehrbenutzer-Rollenmodell: Für einen öffentlichen Betrieb sind Authentifizierung, HTTPS, Zugriffsschutz und ein geeigneter Produktionsserver notwendig. `HOST=0.0.0.0` nur in einer entsprechend geschützten Umgebung verwenden.

## Workflow

1. Vier klar markierte, vollständig fiktive Beispiele zeigen den Ablauf. Es gibt keine behaupteten echten LinkedIn-Beiträge und keine erfundenen Original-URLs. Die Demo-Zeiten werden relativ zur aktuellen Zeit erzeugt und sind ausschließlich Beispieldaten.
2. „Beitrag hinzufügen“ nimmt einen echten Beitragslink, Namen, optionalen persönlichen Profillink, Autorenart, Veröffentlichungszeit und den Originaltext entgegen. Es erfolgt **kein Abruf des Links**. Inhalt und Angaben müssen manuell aus einer zulässigen Quelle übernommen werden. Ein Link allein reicht nicht für Bewertung und Kommentare. Die Browser-Zeitzone wird in einen UTC-Zeitpunkt umgerechnet.
3. Beiträge innerhalb von einschließlich 24 Stunden mit bestätigter Autorenart „Persönliches Profil“ und passendem Themenbezug werden bewertet. Zukunftszeiten, Unternehmensseiten, unbekannte Autorenart und eindeutige Verkaufssignale werden ausgeschlossen. Die manuellen Angaben bleiben unverifiziert.
4. Themen, Mindestbewertung und Datenquelle filtern die Liste. Ausgeschlossene und als ungeeignet markierte Beiträge sind standardmäßig verborgen und können separat eingeblendet werden.
5. Pro geeignetem Beitrag mit ausreichendem Inhalt gibt es genau drei Optionen: fachlicher Mehrwert, dialogorientiert, Lernperspektive der heise academy. Option auswählen, Text bearbeiten, speichern oder kopieren. Ungeeignete Beiträge lassen sich ausblenden und wieder aufnehmen.
6. „Neu formulieren“ erzeugt eine andere regelbasierte Variante und verwirft nach Rückfrage gespeicherte Änderungen. Entwürfe, gewählte Option und Markierungen bleiben in SQLite gespeichert. Die Varianten sind begrenzt und wiederholen sich nach mehreren Aufrufen; es wird kein Sprachmodell angesprochen.
7. Original öffnen, Fakten und Ton prüfen und einen Kommentar bei Bedarf **selbst manuell** auf LinkedIn veröffentlichen. Die App besitzt keine Veröffentlichungsfunktion.

## Bewertung und Grenzen

Die nachvollziehbaren Regeln liegen in `app/domain.py`. Die Anzeige enthält Themenbegründung, Warnungen, Ausschlussgründe und die vier Punktanteile:

- Thematische Relevanz: bis 40 Punkte, anhand der konfigurierten Themenbegriffe.
- Aktualität: bis 25 Punkte, linear abnehmend innerhalb des 24-Stunden-Fensters.
- Diskussionspotenzial: bis 20 Punkte, anhand von Fragen und Begriffen zu Erfahrungen, Learnings und Herausforderungen.
- Qualität / Informationsgehalt: bis 15 Punkte, anhand des Textumfangs und vorhandenen Kontexts.

Verkaufssignale wie „jetzt buchen“, Rabattcodes oder explizite Angebote werden geprüft. Marken- und Produktnennungen allein schließen einen Beitrag nicht aus. Negierte oder kritisch besprochene Werbesprache wird berücksichtigt. Diese Heuristik kann Absicht, Ironie und Qualität nicht zuverlässig semantisch verstehen: Ergebnisse brauchen eine menschliche Prüfung. Es gibt keinen Anspruch auf vollständige Werbeerkennung.

Unter 18 Wörtern oder 110 Zeichen wird ein Kontexthinweis statt künstlicher Kommentare angezeigt. Entwürfe verankern sich über einen tatsächlichen Textausschnitt und eine zum Thema passende Perspektive; sie behaupten keine eigenen Erfahrungen, Leistungsversprechen oder Kursangebote. Fachliche Feinheiten müssen vor Nutzung redaktionell angepasst werden. Dies ist ein regelbasierter Assistent, keine freie KI-Textgenerierung.

## Zulässige Datenquelle anbinden

`app/providers.py` definiert `PostProvider.fetch() -> list[dict]` und den separaten `DemoProvider`. `app/server.py:all_posts()` führt die aktuelle Demoquelle und manuelle SQLite-Imports zusammen. Ein zukünftiger Anbieter wird dort statt bzw. neben `DemoProvider` angebunden; Filter und Frontend bleiben unabhängig von der Beschaffung.

Ein Provider muss mindestens liefern:

```python
{
    'id': 'anbieter-eindeutige-id',
    'source': 'authorized-provider',
    'author': 'Autorname',
    'author_type': 'person',  # company / unknown werden ausgeschlossen
    'profile_url': 'https://www.linkedin.com/in/...',  # optional, sonst ''
    'url': 'https://www.linkedin.com/posts/...',
    'published_at': '2026-10-13T08:00:00+00:00',  # tatsächlicher Zeitpunkt mit Zeitzone
    'text': 'Tatsächlicher Originaltext'
}
```

Automatische Recherche, verifizierte Profile und verifizierte Veröffentlichungszeiten benötigen einen für diesen konkreten Zweck autorisierten Datenanbieter mit den entsprechenden Nutzungsrechten. Allgemeine LinkedIn-API-Zugänglichkeit garantiert diese Rechte oder Suchmöglichkeiten nicht. Vor Integration Datenvertrag, Pagination, Zeitstempel, Löschung, Ratenlimits und zulässige Nutzung prüfen. Keine privaten LinkedIn-Endpunkte oder Scraper einsetzen. Eventuelle Anbieter-Zugangsdaten ausschließlich aus Umgebungsvariablen lesen; niemals im Code, in SQLite, Logs oder Beispielen speichern. Aktuell sind keine Zugangsdaten erforderlich.

## Tests

```bash
python3 -m unittest discover -v
node --check static/app.js  # optional: JavaScript-Syntax, benötigt Node.js
```

Die Tests prüfen Zeitgrenzen einschließlich Zukunft und Zeitzonen, persönliche / Unternehmens- / unbekannte Autoren, Werbeerkennung und nichtwerbliche Produktnennungen, Bewertung, drei unterschiedliche Kommentaroptionen, fehlenden Kontext, Importvalidierung und HTTP-Endpunkte. API-Tests starten einen echten lokalen Server mit temporärer Datenbank und prüfen Import, Speicherung, Neuformulierung und Origin-Schutz.

Optionaler Browser-Smoke-Test (Playwright und Chromium erforderlich):

```bash
python3 -m pip install playwright
# Chromium muss unter /usr/bin/chromium verfügbar sein.
python3 tests/browser_smoke.py
```

Er prüft das echte Dashboard einschließlich Filter, Auswahl, Bearbeitung, Persistenz, ungeeignet / wieder aufnehmen, Import, Originallink und mobiles Layout. Verwendet eine temporäre Datenbank; technische Testdaten werden anschließend gelöscht. Playwright ist keine Laufzeitabhängigkeit und besucht nur die eigene lokale App, niemals LinkedIn.

## Struktur

- `app/domain.py`: Auswahl, Bewertung und Kommentaroptionen
- `app/providers.py`: Datenanbieter-Vertrag und fiktive Demoquelle
- `app/server.py`: HTTP-API, Importvalidierung und SQLite-Speicherung
- `static/`: responsives Dashboard ohne Frontend-Abhängigkeiten
- `tests/`: Domain-, API- und optionaler Browser-Smoke-Test

Die App rendert manuelle Inhalte als Text, verwendet eine restriktive Content Security Policy und begrenzt Eingabegrößen. Links werden beim manuellen Import auf LinkedIn-HTTPS-URLs geprüft. Daten liegen lokal; es werden keine Inhalte an ein Sprachmodell oder LinkedIn gesendet.
