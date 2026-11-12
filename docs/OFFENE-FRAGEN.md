# Offene Fragen

Stellen, an denen das Konzept etwas offenlässt oder mehrdeutig ist. Für jede wurde die kleinste plausible Annahme getroffen und im Code mit `# ASSUMPTION:` markiert. Bitte entscheiden; bis dahin gilt die Annahme.

| Nr. | Regel | Problem | Annahme |
| --- | --- | --- | --- |
| 1 | Eingabe | Das Konzept nennt Kennungen „Text“; Exporte liefern oft Zahlen. | Ganzzahlige Kennungen in JSON (auch in `depends_on` und `parent`) werden als Text gelesen. |
| 2 | Eingabe | Leere Einträge in Listenfeldern (z. B. `a\|\|b` in CSV). | Leere Einträge werden verworfen; Indizes wie `acceptance_criteria[1]` zählen nur nicht leere Einträge. |
| 3 | Eingabe | Zahlenformat der Schätzung in CSV. | Dezimalkomma wird akzeptiert (`2,5`), wie es Excel auf Deutsch schreibt. |
| 4 | Eingabe | Was über die genannten Fehler hinaus ungültig ist. | Auch falsche Typen und Werte führen zu einem Fehler mit Zeilenangabe: Schätzung keine Zahl oder negativ, `rank` keine Ganzzahl ab 1, Priorität nicht MoSCoW. `kind` und `priority` sind unabhängig von Groß-/Kleinschreibung. Unbekannte Spalten oder Felder werden ignoriert. |
| 5 | Eingabe | Unbekannte Kennungen in `depends_on` oder `parent`. | Kein Fehler und kein Befund; sie werden bei den Regeln übergangen (BC-12 behandelt einen unbekannten `parent` wie keinen). |
| 6 | Eingabe | Trennzeichen der CSV-Zellen (Excel auf Deutsch schreibt `;`). | Erkannt an der Kopfzeile (häufigstes aus `,` `;` Tab); auf der Kommandozeile mit `--delimiter` festlegbar. |
| 7 | Eingabe | Zeilenangabe bei der Programmschnittstelle `check()`. | Wird `check()` mit Wörterbüchern aufgerufen, ist die „Zeile“ die Position in der Liste, ab 1. |
| 8 | Ausgabe | Zählweise von Indizes und `span`. | Indizes wie `acceptance_criteria[0]` zählen ab 0. `span` ist `[Anfang, Ende]` in Zeichen (Unicode-Codepunkte), Ende ausschließlich. |
| 9 | Ausgabe | Form der JSON-Ausgabe der Kommandozeile mit Zusammenfassung. | Ein Objekt `{"findings": [...], "summary": {...}}`. |
| 10 | Konfiguration | „Wortliste je Sprache, erweiterbar“: ersetzen oder ergänzen? | Eine angegebene Liste ersetzt die Standardliste dieser Sprache; nicht angegebene Sprachen behalten ihre Standardliste. Gilt ebenso für die zusätzlichen Listen `benefit_patterns`, `conjunctions`, `units`, `term_stopwords`. |
| 11 | Konfiguration | BC-10/BC-11 „lassen sich nicht über `warning` anheben“. | `error` für diese Regeln ist ein Konfigurationsfehler (Rückgabewert 2), keine stille Kappung. |
| 12 | Konfiguration | `ignore` unterdrückt „genau diesen Befund“, ein Eintrag hat aber nur Regel-ID und Kennung. | Unterdrückt werden alle Befunde dieser Regel an diesem Eintrag, keine anderen. |
| 13 | Kommandozeile | `--lang` und `language` in der Konfiguration. | `--lang` bestimmt die Sprache des Berichts. Für die Prüfung gilt `language` aus der Konfigurationsdatei, sonst ebenfalls `--lang`. |
| 14 | Schwellen | „über der Schwelle“ bei BC-03 und BC-10. | Streng größer: Schätzung 13 bei Schwelle 13 löst nicht aus, Ähnlichkeit 0,8 bei Schwelle 0,8 ebenfalls nicht. |
