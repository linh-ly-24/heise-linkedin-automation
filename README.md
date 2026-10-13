# heise academy · Dialogstudio

Assistent für die Recherche relevanter persönlicher LinkedIn-Beiträge und drei deutsche Kommentarentwürfe. Bestehendes Dashboard, manueller Import und SQLite bleiben erhalten. **Keine automatische Veröffentlichung, Likes, Nachrichten, LinkedIn-Scraper, Browser-Bots oder Session-Cookies.**

## Schnellstart auf dem Mac

1. Die aktuellen Projektdateien herunterladen oder nach Freigabe den entsprechenden GitHub-Branch klonen. Die Cloud-Änderungen werden nicht automatisch nach GitHub übertragen.
2. Python 3.12 oder neuer installieren, beispielsweise von [python.org](https://www.python.org/downloads/macos/). Im Terminal mit `python3 --version` prüfen.
3. In den Projektordner wechseln und starten:

   ```bash
   cd ~/Downloads/heise-linkedin-automation
   python3 -m app.server
   ```

   Für die Anwendung sind keine zusätzlichen Python-Pakete, Node.js oder Builds erforderlich. In Codex lautet der Projektpfad `/workspace/heise-linkedin-automation`.
4. Im Browser `http://127.0.0.1:8000` eingeben. Terminal offen lassen. Mit Ctrl+C beenden.
5. Ohne konfigurierte Dienste startet die App im **echten manuellen Modus** mit vorhandenen Imports oder einer leeren Liste. „Demo-Modus (fiktive Daten)“ bewusst aktivieren, um vier Beispiele mit klar markierten **Demo-Textvorlagen** auszuprobieren. Diese sind keine KI-Ausgabe.

Die Cloud-Onboarding-Oberfläche bietet keinen öffentlich erreichbaren Browser-Vorschauzugang. Eine Loopback-Adresse dort ist keine Adresse auf deinem Mac. Lokal ist der oben beschriebene Browserzugriff möglich.

Bei „Address already in use“ läuft bereits ein Server: im ursprünglichen Terminal Ctrl+C drücken oder mit `PORT=8080 python3 -m app.server` einen anderen Port verwenden und im Browser Port 8080 öffnen. Nicht unbekannte Prozesse beenden.

## Workflow: Kandidat → verifizierter Beitrag → Entwurf → Prüfung

### Manuelle Recherche und Import

Auf LinkedIn selbst recherchieren. „Beitrag hinzufügen“ nimmt Beitragslink, Autor, persönlichen Profillink, Autorenart, Originaltext, Veröffentlichungszeit und einen Zeitbeleg entgegen. Fehlende Angaben dürfen für den ersten Import leer bleiben. Die berechtigte lokale Verarbeitung muss bestätigt werden.

Ein Import ist **unverifiziert** und erhält keine KI- oder Vorlagen-Kommentare. „Original prüfen & verifizieren“ öffnen, den Originalbeitrag selbst ansehen und vollständigen Originaltext, Autorenart sowie die tatsächliche Veröffentlichungszeit prüfen. Alle Bestätigungen und ein Zeitbeleg sind erforderlich. Der Suchausschnitt darf nicht als Originaltext und die Fundzeit niemals als Veröffentlichungszeit verwendet werden.

Die Kennzeichnung „menschlich verifiziert“ dokumentiert die manuelle Prüfung; sie behauptet keine Bestätigung durch LinkedIn. Verifizierte Unternehmensseiten, Beiträge über 24 Stunden, Zukunftszeiten, irrelevante oder eindeutig werbliche Inhalte bleiben ausgeschlossen. Unbekannte Autorenart bleibt ausgeschlossen. Geschätzte oder nicht belegbare Zeitangaben erlauben keine zuverlässige Verifikation: nicht bestätigen, wenn das Original keine hinreichende Information liefert.

### Optional: öffentlich indexierte Links suchen

Nach Einrichtung des Suchdienstes ein Thema auswählen und „Indexierte Links suchen“ ausdrücklich bestätigen. Brave liefert Suchergebnisse über seinen Suchindex. **Die App ruft niemals LinkedIn-Seiten ab.** Nur gültige LinkedIn-Beitragslinks werden als Kandidaten gespeichert; gleiche URLs mit unterschiedlichen Tracking-Parametern werden dedupliziert.

Kandidaten zeigen Quelle, Titel, Suchausschnitt, Originallink und Fundzeit. Autorentyp und Veröffentlichungszeit bleiben unbekannt. Ergebnisse können alt, unvollständig oder nicht zugänglich sein. Die Suche garantiert weder persönliche Autoren noch die letzten 24 Stunden oder vollständige LinkedIn-Abdeckung. Kandidaten werden erst nach der oben beschriebenen menschlichen Prüfung zu echten Beiträgen. Bei fehlenden Daten bleibt der Kandidat unverifiziert.

### Echte KI-Kommentare und menschliche Prüfung

Für einen geeigneten, verifizierten Beitrag mit mindestens 18 Wörtern und 110 Zeichen auf „KI-Kommentare erzeugen“ klicken. Die autorisierte Übermittlung des Originaltexts an OpenAI bestätigen. Die App erzeugt und validiert:

- A: konkreter fachlicher Mehrwert.
- B: natürliche, dialogorientierte Reaktion, optional mit Anschlussfrage.
- C: passende Lern- oder Kompetenzperspektive; bei unpassendem Weiterbildungsbezug eine andere konstruktive Reflexion.

Es werden genau drei unterschiedliche Optionen gespeichert, oder ein Kontexthinweis ohne künstliche Kommentare. Prompt und Formatprüfung verhindern keinen fachlichen Fehler vollständig. Fakten, Originalbezug und Ton bleiben menschlich zu prüfen.

Option wählen, bearbeiten und speichern. „Als geprüft markieren“ bestätigt die aktuelle Fassung. **Kopieren ist für echte Entwürfe erst nach dieser Prüfung aktiv.** Änderungen oder eine Neugenerierung machen die Prüfung ungültig. Neuformulierung kostet einen weiteren API-Aufruf; vorhandene menschliche Bearbeitungen bleiben erhalten. Die App veröffentlicht nichts. Ein gespeicherter Text kann technisch auch außerhalb der App kopiert werden: die Prüfung ist ein redaktioneller Workflow, keine LinkedIn-Zugangskontrolle.

Bei API-Fehlern erscheint ein verständlicher Fehler; bestehende Entwürfe bleiben erhalten. Es gibt **keinen stillen Rückfall von echter KI zu Textvorlagen**. Vorlagen sind ausschließlich für fiktive Beispiele im bewusst aktivierten Demo-Modus verfügbar.

## OpenAI sicher konfigurieren

Voraussetzungen: ein für diese Verarbeitung autorisierter API-Zugang, aktivierte API-Abrechnung und ein zugängliches Modell. Ein ChatGPT Pro/Plus-Abonnement stellt nicht automatisch API-Guthaben oder einen API-Key bereit.

1. Nutzungsrechte und Datenschutz für die Weitergabe der Originaltexte prüfen. Den erforderlichen Vertrag zur Auftragsverarbeitung und die Anbieter-Datenrichtlinien prüfen.
2. Im [OpenAI API-Dashboard](https://platform.openai.com/api-keys) einen Schlüssel anlegen. Nicht in Chat, Quellcode, GitHub, Browserfelder oder Logs einfügen.
3. Im Mac-Terminal vor dem Start sicher einlesen (bash und zsh; Eingabe bleibt unsichtbar und nicht im Befehlsverlauf):

   ```bash
   printf 'OpenAI API-Schlüssel (Eingabe unsichtbar): '
   read -r -s OPENAI_API_KEY
   printf '\n'
   export OPENAI_API_KEY
   export OPENAI_MODEL=gpt-4.1-mini
   export OPENAI_PROCESSING_AUTHORIZED=true
   python3 -m app.server
   ```

   Setze die Freigabe nur nach tatsächlicher Prüfung. Ein Schlüssel allein reicht nicht. Für einen Dienstbetrieb Schlüssel über die sichere Umgebungsvariablenverwaltung des Hosts injizieren. In dieser Cloud können reservierte Variablennamen wie `OPENAI_API_KEY` eine Plattformgrenze sein; dann ist die echte KI dort erst nutzbar, wenn eine unterstützte sichere Injection dieses exakten Namens verfügbar ist. Die App liest ausschließlich `OPENAI_API_KEY` aus der Serverumgebung.
4. Im Dashboard muss „OpenAI bereit“ erscheinen. Das bedeutet **nur**, dass Key und Freigabe vorhanden sind; tatsächliche API-Berechtigung, Modellzugang und Guthaben werden erst beim ausdrücklich ausgelösten Aufruf geprüft.

`gpt-4.1-mini` ist ein wirtschaftlicher Ausgangspunkt mit dokumentierter Unterstützung für strukturierte Antworten. Die App verwendet Chat Completions mit JSON Schema und maximal 1.500 Ausgabetokens. Andere Modelle müssen diese Funktionen unterstützen; `OPENAI_MODEL` ist konfigurierbar. Modellverfügbarkeit im eigenen Konto und aktuelle Preise vor Aktivierung prüfen:

- [Modellbeschreibung GPT-4.1 mini](https://platform.openai.com/docs/models/gpt-4.1-mini)
- [Strukturierte Antworten](https://platform.openai.com/docs/guides/structured-outputs)
- [Aktuelle API-Preise](https://openai.com/api/pricing/)
- [OpenAI API-Datenverwendung](https://platform.openai.com/docs/guides/your-data)

**Validierungsstand:** In der Implementierungsumgebung fehlen echte Keys; die offiziellen Modell-, Preis- und Suchdokumentationsseiten wurden vom Netzwerkproxy blockiert. Aktuelle Verfügbarkeit/Preise und ein erfolgreicher Live-Aufruf sind daher nicht bestätigt. Die Integration und Fehlerbehandlung wurden ausschließlich mit gemockten Antworten getestet. Die App behauptet keinen bereits funktionierenden Live-Zugang.

## Optionalen Suchanbieter konfigurieren

Implementiert ist ein modularer Adapter für die **Brave Search API** (`GET https://api.search.brave.com/res/v1/web/search`). Eine technische API-Verfügbarkeit ist kein Nachweis, dass jede Weiterverwendung zulässig ist.

Vor Aktivierung Tarif, Zugriff, Speicherung und zulässige Verwendung von Suchergebnissen sowie den konkreten Recherchezweck bestätigen. Wenn diese Rechte nicht vorliegen, den Suchanbieter deaktiviert lassen und manuell recherchieren. Die Integration verspricht keine autorisierten LinkedIn-Volltexte oder allgemein verfügbare LinkedIn-Post-Such-API.

- [Brave Search API und Tarife](https://brave.com/search/api/)
- [Brave Web Search Dokumentation](https://api-dashboard.search.brave.com/app/documentation/web-search/get-started)
- [LinkedIn API-Zugang](https://learn.microsoft.com/en-us/linkedin/shared/authentication/getting-access)
- [LinkedIn Nutzungsbedingungen](https://www.linkedin.com/legal/user-agreement)

Nach Einrichtung eines berechtigten Brave-API-Kontos im selben Terminal:

```bash
printf 'Brave API-Schlüssel (Eingabe unsichtbar): '
read -r -s BRAVE_SEARCH_API_KEY
printf '\n'
export BRAVE_SEARCH_API_KEY
export SEARCH_PROVIDER=brave
export SEARCH_USE_AUTHORIZED=true
python3 -m app.server
```

Die bereits laufende App vor einem Neustart mit Ctrl+C beenden. Nicht zwei Server auf Port 8000 starten. Auch hier ist „bereit“ nur eine Konfigurationsprüfung. Ein echter Live-Aufruf wurde bisher nicht ausgeführt. Die Variablen sind voneinander unabhängig: KI ohne Brave und manuelle Recherche ohne beide Anbieter sind möglich.

## Konfiguration und Kostenlimits

Alle Einstellungen kommen aus der Serverumgebung. `.env`-Dateien werden **nicht automatisch geladen**. Nicht geheime Einstellungen dürfen per `export` gesetzt werden. Niemals Prozessumgebung mit `env`/`printenv` oder Shell-Tracing ausgeben, wenn sie Keys enthält.

| Variable | Standard | Zweck |
| --- | --- | --- |
| `HOST` | `127.0.0.1` | Nur lokaler Zugriff empfohlen |
| `PORT` | `8000` | HTTP-Port |
| `APP_DB` | `.local/app.sqlite3` im Projekt | Persistente lokale SQLite-Daten |
| `OPENAI_API_KEY` | nicht gesetzt | Nur serverseitiger API-Schlüssel |
| `OPENAI_MODEL` | `gpt-4.1-mini` | Modell mit strukturierten Antworten |
| `OPENAI_PROCESSING_AUTHORIZED` | false | Freigabe nach Rechte-/Datenschutzprüfung |
| `SEARCH_PROVIDER` | `none` | `none` oder `brave` |
| `BRAVE_SEARCH_API_KEY` | nicht gesetzt | Server-Key für Brave |
| `SEARCH_USE_AUTHORIZED` | false | Freigabe nach Anbieter-/Nutzungsprüfung |
| `MAX_AI_CALLS_PER_DAY` | 10 | Maximal 10 Anbieter-Versuche je UTC-Tag |
| `MAX_SEARCH_CALLS_PER_DAY` | 5 | Suchversuche je UTC-Tag |
| `MAX_POSTS_PROCESSED_PER_DAY` | 10 | Unterschiedliche Beiträge mit KI-Versuchen je UTC-Tag |
| `MAX_SEARCH_RESULTS` | 10 | Ergebnisse pro Suchanfrage, 1–20 |
| `PROVIDER_TIMEOUT_SECONDS` | 25 | Timeout pro HTTP-Anfrage, 1–120 Sekunden |
| `DATA_RETENTION_DAYS` | 30 | Aufbewahrungsfrist für explizite Bereinigung |

Limits werden atomar in SQLite reserviert. Fehlerhafte Anbieter-Versuche zählen mit; es gibt keine automatischen Wiederholungen. Fehlende Keys/Freigaben und Cache-Treffer verbrauchen keine Aufrufe. Pro Beitrag werden parallele KI-Anfragen blockiert. Bei einem Prozessabbruch verfällt die Sperre; der Versuch bleibt gezählt.

**Keine Suche oder KI-Anfrage beim Öffnen/Neuladen.** KI-Ergebnisse werden gespeichert und wiederverwendet. Es gibt aktuell keine geplanten Hintergrundjobs; alle Anbieteraufrufe benötigen einen bestätigten Benutzerklick.

Demo und manueller Import haben keine zusätzlichen Daten- oder KI-API-Kosten. OpenAI berechnet Tokens nach Modell; Brave nach Tarif. Hosting kann separat kosten. Ein Beispielvolumen von 20 Beiträgen täglich mit 2.000 Eingabe- und 500 Ausgabetokens je Beitrag ergibt bei 30 Tagen etwa 1,2 Mio. Eingabe- und 0,3 Mio. Ausgabetokens, ohne Neugenerierungen. Mit aktuellen Tokenpreisen multiplizieren; dieses Volumen erfordert eine bewusste Erhöhung der Standardlimits. Es wird kein aktueller Eurobetrag oder kostenloses Suchkontingent zugesichert. Anbieter-Abrechnung zusätzlich prüfen: die lokalen Aufruflimits sind kein exaktes Geldbudget und teilen keine Nutzung anderer Apps mit demselben API-Konto.

## Daten, Sicherheit und Aufbewahrung

- Originaltexte werden nur nach Freigabe und bestätigter KI-Aktion an `api.openai.com` gesendet. Namen, Profil-URLs und Veröffentlichungszeiten werden nicht im KI-Payload benötigt; der Originaltext selbst kann personenbezogene Angaben enthalten. Vor Übermittlung prüfen und minimieren.
- An `api.search.brave.com` gehen nur die konfigurierten thematischen Suchabfragen. Es werden keine manuellen Originaltexte oder persönlichen Profile zur Suchanfrage hinzugefügt.
- Keine automatische Anfrage an `linkedin.com`. Browserlinks werden ausschließlich von einem Menschen geöffnet.
- API-Schlüssel bleiben im Serverprozess. Status-API liefert nur Präsenz-/Freigabestatus; keine Werte. HTTP-Logs enthalten keine Bodies oder Suchabfragen. TLS-Verifikation bleibt aktiv; Redirects werden nicht verfolgt, damit Credentials nicht weitergereicht werden.
- Die lokale Datenbank enthält personenbezogene Imports, Kandidaten und Entwürfe. `.gitignore` schließt `.local/`, Datenbanken, Keys/`.env`, Logs und Python-Caches aus. Bereits anderweitig getrackte sensible Dateien müssten separat behandelt werden; Keys nie committen.
- Die Datenbank liegt in Klartext auf dem lokalen Rechner. Zugriffsschutz und Backup entsprechend gestalten. Vor Updates Server stoppen und die `.local/app.sqlite3` sichern.
- Bestehende Daten und Bearbeitungen bleiben erhalten. Neue Tabellen werden additiv angelegt. Altbestände ohne Verifikationsstatus werden als unverifiziert angezeigt; frühere Bearbeitungen bleiben lesbar.
- „Aufbewahrung prüfen“ zeigt Einträge älter als `DATA_RETENTION_DAYS`. **Nur nach ausdrücklicher Bestätigung** werden diese Einträge und zugehörige Entwürfe gelöscht. Es gibt keine automatische Löschung. Altbestände ohne bekanntes Erfassungsdatum bleiben erhalten und müssen separat geprüft werden. Diese explizite Bereinigung regelmäßig durchführen, wenn die App echte personenbezogene Daten speichert.
- Kein Login/Mehrbenutzer-Rollenmodell. Der Server bindet standardmäßig an Loopback. Für öffentlichen Betrieb sind Authentifizierung, HTTPS, ein passendes Betriebskonzept und Produktionsserver nötig. `HOST=0.0.0.0` nicht ungeschützt verwenden. Der aktuelle Origin-Schutz ist auf den lokalen HTTP-Betrieb ausgelegt.

## Tests ohne API-Kosten

Im Projektordner:

```bash
python3 -m unittest discover -v
```

Die vollständige Suite enthält die ursprünglichen fachlichen Tests sowie neue gemockte Provider-/HTTP-Tests. Sie testet Zeitgrenzen/Zeitzonen, Verifikation, unbekannte Zeiten, Unternehmensseiten, Werbung versus Produktnennung, URLs/Duplikate, fehlende Keys/Freigaben, Timeouts, Ratenlimits, ungültige und zu ähnliche Kommentare, genau A/B/C, Caching, Persistenz, unveränderte Bearbeitungen, geprüfte Entwürfe, Limits und explizite Aufbewahrung. Keine echten API-Keys oder Aufrufe erforderlich.

Optional JavaScript-Syntax prüfen (Node.js erforderlich):

```bash
node --check static/app.js
```

Optionaler interaktiver Browser-Smoke-Test mit Headless-Chromium, ebenfalls mit gemockten Anbietern:

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
python3 tests/browser_smoke.py
```

Der Test startet die lokale App mit temporärer Datenbank. Er testet den Demo-Modus, Import, Verifikation, fehlende Keys, gemockte echte KI-Ausgaben und Suche, Bearbeitung/Persistenz, Prüfung vor Kopieren und mobiles Layout. Er besucht niemals LinkedIn. Bei vorhandenem `/usr/bin/chromium` wird dieses verwendet; alternativ `CHROMIUM_EXECUTABLE` setzen. Keine persönlichen Bestandsdaten werden überschrieben.

## Architektur und Erweiterung

- `app/providers.py`: bestehender `PostProvider`/`DemoProvider`, neuer `SearchProvider`/`BraveSearchProvider`.
- `app/generators.py`: `CommentGenerator`, `OpenAICommentGenerator`, klar getrennter `DemoCommentGenerator`, Ausgabevalidierung.
- `app/domain.py`: bestehende nachvollziehbare Bewertung und Demo-Vorlagen, einschließlich Linux/Open Source. Die Werbe-/Qualitätseinschätzung ist weiterhin heuristisch und benötigt menschliche Prüfung.
- `app/links.py`: erlaubte Links und kanonische URLs ohne Tracking-Parameter.
- `app/config.py`: nicht öffentliche Serverkonfiguration.
- `app/transport.py`: begrenzte JSON-Anfragen, verifiziertes TLS und sichere Fehlermeldungen.
- `app/storage.py`: additive Speicherung, Cache, Aufruflimits, kurzlebige Sperren und explizite Aufbewahrung.
- `app/server.py`: bestehender HTTP-Server, Status-, Import-, Verifikations-, Such-, Generierungs- und Review-Endpunkte.
- `static/`: bestehendes Design mit klaren Quellen-/Workflow-Labels und Dienststatus.
- `tests/`: Unit-, Integrations- und optionaler Browser-Smoke-Test.

Suchtreffer und bestätigte Beiträge sind bewusst unterschiedliche Datentypen. Ein weiterer **autorisierter** Anbieter implementiert `SearchProvider.search(topic)` und wird in `search_provider()` registriert. Sein Adapter muss Datenrechte, feste HTTPS-Destinationen, tatsächliche Felder und Limits berücksichtigen. Ein Kandidat enthält `url`, `source_url`, `title`, `snippet`, `discovered_at`, `published_at=None`, `author_type='unknown'` und `status='candidate'`. Selbst ein Volltextanbieter darf fehlende Originaldaten nicht ergänzen; menschliche Verifikation bleibt erforderlich.

Die App enthält keine allgemeine LinkedIn-Such-API, keinen Login bei LinkedIn und keinen Code, der Beiträge automatisiert veröffentlicht. Eine technische Suchmaschinenanbindung ersetzt keine Prüfung der Nutzungsrechte.
