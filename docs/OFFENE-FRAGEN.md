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
| 15 | BC-02 | Mehrere vage Wörter in einem Kriterium. | Ein Befund je Fundstelle, in Textreihenfolge; `params.word` ist das Wort, wie es im Text steht. Maßeinheiten stehen als Liste `units` in der Konfiguration. |
| 16 | BC-03, BC-04, BC-06 | „Eintrag“ statt „Story“: gelten die Regeln auch für Epics und Bugs? | Ja, für alle Arten, wie im Wortlaut. |
| 17 | BC-04 | „Mehrere Tätigkeiten“ lassen sich ohne Grammatikanalyse nicht sicher erkennen; was ist der „Nutzensatz“? | Jedes „und“/„and“ als ganzes Wort zählt (Schwere `info`). Geprüft werden der Titel und jeder Satz der Beschreibung, der ein Nutzensatz-Muster aus BC-05 enthält. Höchstens ein Befund je Feld. |
| 18 | BC-06 | Bezieht sich „die obersten 20“ auf den Wert von `rank` oder auf die Position unter den offenen Einträgen? | Auf den Wert von `rank` (1 bis 20). |
| 19 | BC-07 | Wie sieht eine Kennung „als ganzes Wort“ aus? Zählen Epic und eigene Kinder? | Kennungen aus Buchstaben, Ziffern, `_`, `-` und `.`, am Anfang und Ende Buchstabe oder Ziffer. Das eigene Epic (`parent`) und eigene Kinder gelten als bekannt und lösen nichts aus. Ein Befund je genannter Kennung, an der ersten Fundstelle. |
| 20 | BC-08 | Einträge ohne `rank` oder ohne Priorität; erledigte Abhängigkeiten. | Verglichen wird nur, was auf beiden Seiten gesetzt ist. Erledigte Abhängigkeiten sind erfüllt und lösen nichts aus. Je Paar ein Befund; trifft beides zu, ein gemeinsamer Schlüssel `bc08.rank_and_priority_order`. |
| 21 | BC-09 | Was ist „ein Kreis“, wenn sich Kreise überlappen? Zählen erledigte Einträge? | Ein Befund je stark zusammenhängender Komponente (alle, die wechselseitig voneinander abhängen), am ersten Beteiligten der Eingabe; Selbstabhängigkeit zählt. Erledigte Einträge zählen nicht mit. |
| 22 | BC-10 | Ähnlichkeitsmaß, Ort des Befunds, erledigte Einträge. | Jaccard-Index der Wortmengen (Kleinschreibung, Wörter aus Buchstaben und Ziffern) von Titel und Beschreibung zusammen. Befund am späteren Eintrag, `related` nennt den früheren. Erledigte Einträge werden nicht verglichen. Vorfilter: Präfixfilter nach Seltenheit der Wörter. |
| 23 | BC-11 | Was ist „derselbe Begriff“? | Das nächste von höchstens drei Wörtern vor der Zahl im selben Satz, das kein Füllwort (`term_stopwords`) ist. Einheiten gelten als gleich, wenn sie laut `units` dieselbe Grundeinheit haben (Tag/Tage/Tagen); umgerechnet wird nicht. Ein Befund je Paar aus Einträgen und Begriff, am späteren Eintrag. |
| 24 | BC-12 | Brauchen Bugs ein Epic? Zählen erledigte Stories und Bugs als Stories eines Epics? | Bugs brauchen kein Epic. Erledigte Stories zählen für ihr Epic, Bugs nicht. Ein `parent`, der unbekannt oder kein Epic ist, zählt wie kein Epic. |
| 25 | Zusammenfassung | Bezugsgröße des Anteils „bereit“. | Anteil der offenen Stories ohne Befund der Schwere `error`; `null`, wenn es keine offenen Stories gibt. |
