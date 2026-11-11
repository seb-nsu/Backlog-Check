# Claude Code – Projektregeln: backlog-check

`backlog-check` prüft einen Backlog gegen feste Regeln und liefert Befunde. Verbindlich ist `docs/KONZEPT.md`: Ein- und Ausgabeformat, die Regeln BC-01 bis BC-12, Konfiguration, Akzeptanzkriterien und Reihenfolge. Regeln werden mit ihrer ID zitiert.

Sprache: Dokumente auf Deutsch; Code, Bezeichner, Kommentare und Commit-Nachrichten auf Englisch.

## Grenzen

- Nur die Python-Standardbibliothek zur Laufzeit. Entwicklungswerkzeuge (pytest, coverage, ruff) sind erlaubt.
- Keine KI, kein Netzwerkzugriff, keine Datenbank, keine Web-Oberfläche.
- Das Paket liefert keine fertigen Sätze: Befunde tragen `message_key` und `params`. Texte stehen nur in den Katalogen für Deutsch und Englisch.
- Gleiche Eingabe ergibt byteweise gleiche Ausgabe. Kein Zufall, keine Uhrzeit, keine Abhängigkeit von der Reihenfolge in Mengen oder Wörterbüchern.
- Schwellen und Wortlisten stehen in der Konfiguration, nie fest im Code der Regeln.
- Das Ein- und Ausgabeformat ist eine Schnittstelle für andere Anwendungen. Ändere es nicht ohne Rückfrage.

## Arbeitsweise

- Reihenfolge wie in `docs/KONZEPT.md`, Abschnitt „Reihenfolge“. Die Golden Cases einer Regel entstehen vor der Regel.
- Je Regel ein Modul oder eine klar abgegrenzte Funktion mit der Regel-ID im Namen und im Testnamen.
- Jede Regel hat mindestens einen Fall, der auslöst, und einen, der knapp nicht auslöst, auf Deutsch und Englisch. Erwartungswerte bestehender Golden Cases nie ohne Rückfrage ändern.
- Abdeckung 100 % der Zeilen und Zweige. Vor jedem Commit: Lint, Tests mit Abdeckung.
- Fehlt etwas im Konzept oder widerspricht es sich: nicht still entscheiden. Die kleinste plausible Annahme treffen, im Code mit `# ASSUMPTION:` markieren und in `docs/OFFENE-FRAGEN.md` eintragen (Regel-ID, Problem, Annahme).
- Kleine Commits, je Regel einer. Arbeit auf einem Branch mit Pull Request gegen `main`; `main` bleibt immer grün.
- Keine echten Firmen-, Kunden- oder Personennamen in Testdaten.

## Startauftrag

```
Lies CLAUDE.md und docs/KONZEPT.md vollständig.
Baue das Paket backlog-check in der Reihenfolge aus dem Konzept: 1. Datentypen, Einlesen und Validieren,
2. Golden Cases für alle Regeln, 3. Regeln BC-01 bis BC-12, 4. Zusammenfassung und Textkataloge,
5. Kommandozeile, 6. Referenz-Backlog, Leistungstest und README.
Richte dabei eine CI ein, die Lint und Tests mit Abdeckung ausführt.
Arbeite im Branch feature/erste-version. Stoppe, wenn alle automatisch prüfbaren Akzeptanzkriterien erfüllt
sind, und öffne einen Pull Request mit den Akzeptanzkriterien als Checkliste; markiere manuelle Kriterien als offen.
```
