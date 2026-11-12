# Konzept: backlog-check

**Stand:** 11.11.2026 · **Status:** freigegeben, noch nicht gebaut

## Zweck

Stories gehen in die Umsetzung, obwohl Akzeptanzkriterien fehlen, sie zu groß sind oder sich widersprechen. Das fällt erst in der Abnahme auf. `backlog-check` prüft einen Backlog vorher gegen feste, nachvollziehbare Regeln.

**Zielgruppe:** Product Owner und Projektleitungen mit einem Backlog aus Jira, Azure DevOps, Excel oder einem anderen Werkzeug.

**Grundsatz:** Jeder Befund kommt aus einer Regel mit ID. Das Paket enthält keine KI und ruft keinen Dienst auf. Gleiche Eingabe ergibt gleiche Ausgabe.

## Lieferumfang

| Teil | Inhalt |
| --- | --- |
| Python-Paket `backlog_check` | Funktion `check(items, config) -> findings`; nur Standardbibliothek |
| Kommandozeile `backlog-check` | Liest CSV oder JSON, schreibt Befunde als JSON, CSV oder lesbaren Text |
| Textkataloge | Deutsch und Englisch für die lesbare Ausgabe der Kommandozeile |

**Nicht Teil des Pakets:** Web-Oberfläche, Datenbank, Anbindung an Jira oder andere Systeme, KI-Vorschläge, Speichern von Ergebnissen. Andere Anwendungen binden das Paket ein und bringen ihre Oberfläche selbst mit.

## Eingabe

Eine Liste von Einträgen. Felder (Pflicht fett):

| Feld | Typ | Bedeutung |
| --- | --- | --- |
| **`id`** | Text | Eindeutige Kennung, z. B. `R1-31` oder `PROJ-123` |
| **`kind`** | `epic`, `story`, `bug` | Art des Eintrags |
| **`title`** | Text | Titel |
| `description` | Text | Beschreibung, darf leer sein |
| `acceptance_criteria` | Liste von Texten | Je Kriterium ein Eintrag |
| `estimate` | Zahl oder leer | Story Points oder Stunden |
| `priority` | `must`, `should`, `could`, `wont` oder leer | Priorität nach MoSCoW |
| `rank` | Ganzzahl oder leer | Position im Backlog, 1 ist oben |
| `status` | Text oder leer | Frei; `done` und `closed` werden von der Prüfung ausgenommen (einstellbar) |
| `depends_on` | Liste von Kennungen | Eingetragene Abhängigkeiten |
| `parent` | Kennung oder leer | Übergeordnetes Epic |
| `updated` | Datum oder leer | Letzte Änderung (`2026-11-12`, `12.11.2026` oder Jira-Format `12/Nov/26 1:06 PM`); für BC-13 |

**CSV:** eine Zeile je Eintrag, Kopfzeile mit den Feldnamen. Listenfelder (`acceptance_criteria`, `depends_on`) trennt ein einstellbares Zeichen, Standard ist der Zeilenumbruch innerhalb der Zelle oder `|`. Die Kommandozeile bildet abweichende Spaltennamen über eine Zuordnung ab (`--map "Summary=title"`), damit Exporte aus Jira und Excel ohne Umbau lesbar sind.

Ungültige Eingaben (fehlendes Pflichtfeld, doppelte Kennung, unbekannte Art) führen zu einem Fehler mit Zeilenangabe, nicht zu einem Befund.

## Ausgabe

Eine Liste von Befunden, sortiert nach Position des Eintrags in der Eingabe, dann nach Regel-ID.

| Feld | Bedeutung |
| --- | --- |
| `rule` | Regel-ID, z. B. `BC-02` |
| `severity` | `info`, `warning` oder `error` |
| `item` | Kennung des Eintrags |
| `related` | Weitere betroffene Kennungen (z. B. die Dublette), sonst leer |
| `field` | Betroffenes Feld, z. B. `acceptance_criteria[2]` |
| `span` | Anfang und Ende der Textstelle im Feld, wenn es eine gibt |
| `message_key` | Schlüssel im Textkatalog, z. B. `bc02.unmeasurable` |
| `params` | Werte für den Text, z. B. `{"word": "schnell"}` |

Das Paket liefert **keine fertigen Sätze**. Den Wortlaut bildet der Aufrufer aus `message_key` und `params`; die Kommandozeile nutzt dafür die mitgelieferten Kataloge. So bleiben Befunde übersetzbar und in Tests stabil.

Dazu eine Zusammenfassung: Zahl der Einträge, Zahl der Befunde je Regel und Schwere, Anteil der Stories ohne Befund der Schwere `error` („bereit“).

## Regeln der ersten Version

| ID | Regel | Prüfung | Standard |
| --- | --- | --- | --- |
| BC-01 | Akzeptanzkriterien fehlen | Story oder Bug ohne Kriterium | error |
| BC-02 | Kriterium nicht prüfbar | Kriterium enthält ein Wort der Wortliste („schnell“, „einfach“, „benutzerfreundlich“, „möglichst“, „etc.“, „fast“, „easy“, „user-friendly“) und im selben Kriterium weder Zahl noch Maßeinheit | warning |
| BC-03 | Eintrag zu groß | Schätzung über der Schwelle (Standard 13) oder mehr als 8 Kriterien | warning |
| BC-04 | Mehrere Anliegen | Titel oder Nutzensatz verbindet mehrere Tätigkeiten mit „und“ bzw. „and“ | info |
| BC-05 | Nutzen fehlt | Story ohne Nutzensatz („damit“, „um … zu“, „so that“, „in order to“) in Titel oder Beschreibung | info |
| BC-06 | Schätzung fehlt | Eintrag mit `rank` bis zur Schwelle (Standard: die obersten 20) ohne Schätzung | warning |
| BC-07 | Versteckte Abhängigkeit | Titel, Beschreibung oder Kriterium nennt die Kennung eines anderen Eintrags, der nicht in `depends_on` steht | warning |
| BC-08 | Abhängigkeit in falscher Reihenfolge | Ein Eintrag steht im `rank` vor einem, von dem er abhängt, oder hat eine höhere Priorität als dieser | warning |
| BC-09 | Zyklus | Abhängigkeiten bilden einen Kreis; der Befund nennt alle Beteiligten | error |
| BC-10 | Mögliche Dublette | Ähnlichkeit von Titel und Beschreibung zweier Einträge über der Schwelle (Wortmengen nach Normalisierung, Standard 0,8) | info |
| BC-11 | Widersprüchliche Werte | Zwei Einträge nennen für denselben Begriff unterschiedliche Zahlen mit Einheit, z. B. „Frist 5 Tage“ und „Frist 10 Tage“ | info |
| BC-12 | Struktur unvollständig | Epic ohne Stories oder Story ohne Epic, wenn der Backlog überhaupt Epics enthält | info |
| BC-13 | Eintrag veraltet | `updated` liegt mehr als `stale_days` (Standard 180) vor dem Stichtag `reference_date`; ohne Stichtag läuft die Regel nicht | info |
| BC-14 | Reproduktion fehlt | Bug, dessen Beschreibung keine Schritte zum Nachstellen enthält (Muster `repro_patterns`) | warning |
| BC-15 | Ziel fehlt | Epic, dessen Beschreibung weniger als `epic_goal_min_words` Wörter hat (Standard 5) | info |

BC-13 bis BC-15 kamen nach Freigabe der ersten Version auf Wunsch dazu (12.11.2026). Ebenso diese Schärfungen:

- BC-04 zählt eine Konjunktion nur, wenn direkt danach ein Verb steht (`activity_patterns`; Deutsch: kleingeschriebener Infinitiv, Englisch: Liste üblicher Verben).
- BC-07 übergeht Nennungen von Einträgen, die vom geprüften Eintrag abhängen (Gegenrichtung).
- BC-10 lässt Füllwörter (`similarity_stopwords`) beim Vergleich weg.
- BC-11 rechnet Einheiten vor dem Vergleich in eine Grundeinheit um (`unit_conversions`, z. B. 2 Wochen = 14 Tage).

Zu den Regeln im Einzelnen:

- BC-10 und BC-11 arbeiten mit einfachen Textverfahren und liefern deshalb nur `info`, nie `error`. Ihre Schwere lässt sich nicht über `warning` anheben.
- BC-02 prüft nur Akzeptanzkriterien, nicht die Beschreibung.
- BC-07 erkennt Kennungen nur als ganzes Wort und nur solche, die in der Eingabe vorkommen.
- BC-08 meldet je Paar einen Befund am abhängigen Eintrag.
- Erledigte Einträge werden nicht geprüft, zählen aber als Ziel von Abhängigkeiten.

## Konfiguration

Ein Objekt mit Standardwerten; jeder Wert ist überschreibbar.

| Einstellung | Standard |
| --- | --- |
| `language` | `de` (alternativ `en`); bestimmt Wortlisten und Nutzensatz-Muster. `auto` prüft beide |
| `rules.<ID>.enabled` | `true` für alle |
| `rules.<ID>.severity` | wie in der Tabelle |
| `max_estimate` | 13 |
| `max_criteria` | 8 |
| `estimate_required_top` | 20 |
| `duplicate_threshold` | 0,8 |
| `done_statuses` | `done`, `closed`, `erledigt`, `abgeschlossen` |
| `vague_words` | Wortliste je Sprache, erweiterbar |
| `ignore` | Liste aus Regel-ID und Kennung für bewusst hingenommene Befunde; als Objekt optional mit `field` und `related`, um einen einzelnen Befund zu treffen |
| `reference_date` | leer; Stichtag für BC-13 (`YYYY-MM-DD`) |
| `stale_days` | 180 |
| `epic_goal_min_words` | 5 |
| `activity_patterns`, `similarity_stopwords`, `unit_conversions`, `repro_patterns` | Wortlisten und Muster je Sprache bzw. Umrechnungstabelle, erweiterbar |

Die Kommandozeile liest die Konfiguration aus einer JSON-Datei (`--config`).

## Kommandozeile

```
backlog-check backlog.csv                       # lesbarer Bericht auf Deutsch
backlog-check backlog.json --format json        # Befunde als JSON
backlog-check backlog.csv --lang en --config regeln.json
backlog-check backlog.csv --map "Summary=title" --map "Issue key=id"
backlog-check jira-export.csv --preset jira      # fertige Zuordnung für Jira (ebenso azure-devops)
backlog-check backlog.csv --format markdown      # Bericht für Wiki-Seiten
backlog-check backlog.csv --format sarif         # SARIF 2.1.0 für Code-Plattformen
backlog-check backlog.csv --reference-date 2026-11-12
```

Rückgabewert: 0 ohne Befund der Schwere `error`, 1 mit, 2 bei ungültiger Eingabe. Damit lässt sich die Prüfung in eine CI einbauen.

## Qualität

- **Golden Cases:** je Regel mindestens ein Fall, der auslöst, und einer, der knapp nicht auslöst, jeweils auf Deutsch und Englisch, mit von Hand festgelegter Erwartung.
- **Abdeckung:** 100 % der Zeilen und Zweige des Pakets.
- **Determinismus:** zweimal dieselbe Eingabe ergibt byteweise dieselbe Ausgabe; keine Abhängigkeit von Reihenfolgen in Mengen oder Wörterbüchern.
- **Referenz-Backlog:** ein größerer, frei verwendbarer Beispiel-Backlog als Regressionstest unter `tests/data/`. Ziel für die erste Version: Bei Durchsicht von Hand sind mindestens 70 % der Befunde der Schwere `warning` und `error` berechtigt.
- **Leistung:** 1.000 Einträge in unter 2 Sekunden auf einem normalen Laptop; BC-10 darf dafür nicht jeden Eintrag mit jedem voll vergleichen, ohne vorher zu filtern.

## Akzeptanzkriterien

- [ ] Das Paket hat keine Abhängigkeit außer der Standardbibliothek (Entwicklungswerkzeuge wie pytest ausgenommen)
- [ ] Die Kommandozeile prüft eine CSV- und eine JSON-Datei und liefert die Rückgabewerte 0, 1 und 2 wie beschrieben
- [ ] Jede Regel BC-01 bis BC-12 hat Golden Cases auf Deutsch und Englisch
- [ ] Die Abdeckung liegt bei 100 %
- [ ] Zweimal dieselbe Eingabe ergibt byteweise dieselbe Ausgabe
- [ ] Eine abgeschaltete Regel erzeugt keinen Befund; eine geänderte Schwelle wirkt
- [ ] Ein Eintrag in `ignore` unterdrückt genau diesen Befund und keinen anderen
- [ ] Befunde enthalten keinen fertigen Satz; jeder `message_key` existiert in beiden Katalogen
- [ ] Ungültige Eingabe führt zu einem Fehler mit Zeilenangabe, nicht zu einem Absturz
- [ ] 1.000 Einträge werden in unter 2 Sekunden geprüft
- [ ] README mit Installation, einem Beispiel und der Regeltabelle auf Deutsch und Englisch
- [ ] (manuell) Durchsicht des Referenz-Backlogs: mindestens 70 % der Warnungen und Fehler sind berechtigt

## Reihenfolge

1. Datentypen für Eintrag, Befund und Konfiguration; Einlesen und Validieren von JSON und CSV.
2. Golden Cases für alle Regeln schreiben, bevor die Regeln entstehen.
3. Regeln BC-01 bis BC-06 (je Eintrag), dann BC-07 bis BC-09 (Abhängigkeiten), dann BC-10 bis BC-12 (über mehrere Einträge).
4. Zusammenfassung und Textkataloge.
5. Kommandozeile.
6. Referenz-Backlog, Leistungstest, README.

## Offene Punkte

| Nr. | Frage | Annahme bis zur Entscheidung |
| --- | --- | --- |
| 1 | Veröffentlichung auf PyPI | Nein; Installation direkt aus dem Repository mit fester Version (Tag) |
| 2 | Mindestversion von Python | 3.11 |
| 3 | Weitere Sprachen neben Deutsch und Englisch | Nein |
| 4 | Welcher Referenz-Backlog | Ein eigens erstellter Beispiel-Backlog ohne Daten aus fremden Projekten |

## Verwendung durch CuraPlan

CuraPlan bindet das Paket in fester Version ein und enthält selbst keine Regel-Logik. Es bildet seine Arbeitselemente auf das Eingabeformat ab und die Befunde auf eigene Texte. Daraus folgt für dieses Paket: Das Ein- und Ausgabeformat ist eine Schnittstelle. Änderungen daran brauchen eine neue Hauptversion.
