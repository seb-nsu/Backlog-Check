# backlog-check

Prüft einen Backlog gegen feste Regeln, bevor Stories in die Umsetzung gehen: fehlende Akzeptanzkriterien, nicht prüfbare Kriterien, zu große Stories, versteckte Abhängigkeiten, Zyklen, mögliche Dubletten und Widersprüche. Jeder Befund nennt die Regel und die Textstelle. Das Paket enthält keine KI und braucht nur die Python-Standardbibliothek.

> **English:** see [below](#english).

| Datei | Inhalt |
| --- | --- |
| [docs/KONZEPT.md](docs/KONZEPT.md) | Ein- und Ausgabeformat, die Regeln BC-01 bis BC-18, Konfiguration, Akzeptanzkriterien |
| [docs/OFFENE-FRAGEN.md](docs/OFFENE-FRAGEN.md) | Lücken im Konzept und die bis zur Entscheidung getroffenen Annahmen |
| [CLAUDE.md](CLAUDE.md) | Projektregeln für Claude Code |

## Installation

Python 3.11 oder neuer. Das Paket wird nicht auf PyPI veröffentlicht, sondern mit fester Version aus dem Repository installiert:

```
pip install "git+https://github.com/seb-nsu/Backlog-Check@v0.2.0"
```

Für die Entwicklung:

```
pip install -e ".[dev]"
ruff check . && ruff format --check .
coverage run -m pytest && coverage report
```

## Beispiel

`backlog.csv` (Kopfzeile mit den Feldnamen; Listen in einer Zelle mit Zeilenumbruch oder `|` getrennt):

```
id;kind;title;description;acceptance_criteria;estimate;rank
S-1;story;Medium verlängern;Als Leser möchte ich verlängern, damit ich keine Gebühr zahle.;Die Verlängerung ist einfach.;3;1
S-2;bug;Beleg zeigt falsches Datum;;;;2
```

```
$ backlog-check backlog.csv
2 Einträge, davon 2 geprüft: 3 Befunde

S-1  Warnung  BC-02 Kriterium nicht prüfbar
    Das Kriterium enthält „einfach“, aber weder Zahl noch Maßeinheit, und ist so nicht prüfbar.
    (Feld acceptance_criteria[0]; Textstelle „einfach“)

S-2  Fehler  BC-01 Akzeptanzkriterien fehlen
    Es fehlen Akzeptanzkriterien.
    (Feld acceptance_criteria)

S-2  Warnung  BC-06 Schätzung fehlt
    Der Eintrag steht auf Rang 2 und damit unter den obersten 20, hat aber keine Schätzung.
    (Feld estimate)

Zusammenfassung
    1 Fehler, 2 Warnungen, 0 Hinweise
    ...
```

Weitere Aufrufe:

```
backlog-check backlog.json --format json            # Befunde und Zusammenfassung als JSON
backlog-check backlog.csv --format csv --output befunde.csv
backlog-check backlog.csv --lang en --config regeln.json
backlog-check export.csv --map "Summary=title" --map "Issue key=id" --map "Issue Type=kind"
backlog-check jira-export.csv --preset jira          # fertige Zuordnung für Jira
backlog-check azure-export.csv --preset azure-devops # fertige Zuordnung für Azure DevOps
backlog-check backlog.csv --format markdown          # Bericht für Wiki-Seiten
backlog-check backlog.csv --format sarif             # SARIF 2.1.0 für Code-Plattformen
backlog-check backlog.csv --reference-date 2026-11-12  # Stichtag für BC-13
backlog-check backlog.csv --fail-on warning          # schon Warnungen ergeben Rückgabewert 1
backlog-check backlog.csv --fix --output neu.json    # Backlog mit angewendeten Korrekturen
backlog-check backlog.csv --color never             # ohne Farben (Standard: farbig nur im Terminal)
```

Im Terminal ist der Schweregrad farbig (Fehler rot, Warnung gelb, Hinweis cyan). In Dateien, Pipes und mit der
Umgebungsvariable `NO_COLOR` bleibt die Ausgabe unverändert und byteweise gleich.

### Stories verbessern und neu anlegen

Mit `--suggest` steht unter jedem Befund ein konkreter Vorschlag, wie er sich beheben lässt, in jedem Format (Text, Markdown, JSON, CSV, SARIF):

```
S-7  Warnung  BC-02 Kriterium nicht prüfbar
    Das Kriterium enthält „schnell“, aber weder Zahl noch Maßeinheit, und ist so nicht prüfbar.
    (Feld acceptance_criteria[0]; Textstelle „schnell“)
    Vorschlag: Ersetze „schnell“ durch einen Messwert, z. B. „in höchstens <n> Sekunden“.
```

Die Vorschläge nutzen den Eintrag selbst: Bei BC-04 werden aus „Rechnung erstellen und versenden“ die Titel „Rechnung erstellen“ und „Rechnung versenden“, bei BC-12 wird das Epic mit den meisten gemeinsamen Wörtern genannt. Ohne `--suggest` bleibt die Ausgabe unverändert.

`--template story` (ebenso `bug`, `epic`) gibt einen neuen Eintrag mit Platzhaltern als JSON aus: Nutzensatz „Als <Rolle> möchte ich …, damit …“, Kriterien nach „Gegeben … wenn … dann …“ mit Sonderfall und Messwert; Bugs mit Schritten zum Nachstellen, Epics mit Ziel. Ausgefüllt besteht die Vorlage die Regeln.

```
backlog-check --template story --output neue-story.json
backlog-check backlog.csv --suggest --format markdown
```

### Vorschläge anwenden

`--fix` schreibt den Backlog mit den mechanisch möglichen Korrekturen als JSON im Eingabeformat (nach `--output` oder auf die Standardausgabe) und listet die Änderungen auf der Fehlerausgabe:

```
$ backlog-check backlog.csv --fix --output backlog-neu.json
S-1  BC-04  Geteilt: Der Eintrag heißt jetzt „Rechnung erstellen“, neu ist S-1-2 „Rechnung versenden“.
S-1  BC-07  Abhängigkeit S-2 ergänzt.
S-4  BC-12  Epic E-1 als übergeordneten Eintrag gesetzt.
S-5  BC-18  Kriterium acceptance_criteria[2] gestrichen, es wiederholte acceptance_criteria[0].
4 Änderungen
```

Angewendet werden nur Korrekturen ohne inhaltliche Entscheidung: BC-04 (Titel teilen; der neue Eintrag übernimmt Art, Epic, Priorität und Status, Beschreibung und Kriterien bleiben beim alten), BC-07 (Abhängigkeit eintragen), BC-12 (Epic aus dem Vorschlag setzen, nur bei Stories ganz ohne `parent`) und BC-18 (doppeltes Kriterium streichen). Alles andere bleibt dem Autor überlassen; `--suggest` zeigt, wie. Die Eingabedatei wird nie überschrieben, außer man nennt sie bei `--output`. Rückgabewert `0`. In Python: `apply_fixes(items, findings, config)` gibt den Backlog als Liste und die Änderungen (`Change` mit `message_key`, `params`) zurück.

### GitHub Action und pre-commit

Als Schritt in einem GitHub-Workflow, z. B. mit SARIF-Upload in Code Scanning:

```yaml
- uses: actions/checkout@v4
- uses: seb-nsu/Backlog-Check@v0.2.0
  with:
    file: backlog.csv
    config: backlog-check.json   # optional
    format: sarif                # text, json, csv, markdown, sarif
    output: backlog.sarif        # leer: Bericht im Log
    fail-on: warning             # error (Standard), warning, info, none
    args: --suggest              # weitere Optionen
- uses: github/codeql-action/upload-sarif@v3
  if: always()
  with:
    sarif_file: backlog.sarif
```

Weitere Eingaben: `preset`, `lang`, `python-version`. Als pre-commit-Hook (die Datei steht in `args`, der Hook läuft, wenn sich eine CSV- oder JSON-Datei ändert):

```yaml
repos:
  - repo: https://github.com/seb-nsu/Backlog-Check
    rev: v0.2.0
    hooks:
      - id: backlog-check
        args: [backlog.csv, --fail-on, warning]
```

Die Presets übernehmen Kennung, Art, Titel, Beschreibung, Akzeptanzkriterien, Schätzung, Status, Epic und (Jira) das Änderungsdatum. Priorität, Rang und Verknüpfungen passen nicht ins Eingabeformat und werden nicht übernommen; bei Bedarf mit `--map` ergänzen. Tasks gelten als Story, Azure-DevOps-Features als Epic.

Rückgabewert: `0` ohne Befund der Schwere `error`, `1` mit, `2` bei ungültiger Eingabe oder Konfiguration (mit Zeilenangabe). Mit `--fail-on warning` (oder `info`) führen schon Warnungen (bzw. Hinweise) zu `1`; `--fail-on none` gibt bei gültiger Eingabe immer `0` zurück, etwa wenn nur ein Bericht entstehen soll.

Als Bibliothek:

```python
from backlog_check import check, load_file, render, summarize

items = load_file("backlog.json")
findings = check(items, {"language": "de", "max_estimate": 8})
for finding in findings:
    print(finding.item, finding.rule, render(finding.message_key, finding.params, "de"))
print(summarize(items, findings))

from backlog_check import suggest, template

for hint in suggest(items, findings, {"language": "de", "max_estimate": 8}):
    print(hint.item, hint.rule, render(hint.message_key, hint.params, "de"))
print(template("story", "de"))
```

`check()` nimmt auch eine Liste von Wörterbüchern im Eingabeformat. Befunde enthalten keine fertigen Sätze, sondern `message_key` und `params`; die mitgelieferten Kataloge (`render`) gibt es auf Deutsch und Englisch.

## Regeln

| ID | Regel | Prüfung | Standard |
| --- | --- | --- | --- |
| BC-01 | Akzeptanzkriterien fehlen | Story oder Bug ohne Kriterium | error |
| BC-02 | Kriterium nicht prüfbar | Kriterium enthält ein Wort der Wortliste („schnell“, „einfach“, …) und weder Zahl noch Maßeinheit | warning |
| BC-03 | Eintrag zu groß | Schätzung über der Schwelle (13) oder mehr als 8 Kriterien | warning |
| BC-04 | Mehrere Anliegen | Titel oder Nutzensatz verbindet mehrere Tätigkeiten mit „und“ | info |
| BC-05 | Nutzen fehlt | Story ohne Nutzensatz („damit“, „um … zu“) | info |
| BC-06 | Schätzung fehlt | Eintrag mit `rank` bis 20 ohne Schätzung | warning |
| BC-07 | Versteckte Abhängigkeit | Text nennt die Kennung eines anderen Eintrags, die nicht in `depends_on` steht | warning |
| BC-08 | Abhängigkeit in falscher Reihenfolge | Eintrag steht im `rank` vor einem, von dem er abhängt, oder hat eine höhere Priorität | warning |
| BC-09 | Zyklus | Abhängigkeiten bilden einen Kreis | error |
| BC-10 | Mögliche Dublette | Ähnlichkeit von Titel und Beschreibung über 0,8 | info |
| BC-11 | Widersprüchliche Werte | Zwei Einträge nennen für denselben Begriff unterschiedliche Zahlen mit Einheit | info |
| BC-12 | Struktur unvollständig | Epic ohne Stories oder Story ohne Epic, wenn es Epics gibt | info |
| BC-13 | Eintrag veraltet | `updated` liegt mehr als 180 Tage vor dem Stichtag `reference_date` (nur mit Stichtag) | info |
| BC-14 | Reproduktion fehlt | Bug ohne Schritte zum Nachstellen in der Beschreibung | warning |
| BC-15 | Ziel fehlt | Epic mit weniger als 5 Wörtern Beschreibung | info |
| BC-16 | Platzhalter nicht ausgefüllt | Text enthält noch „<…>“, „TODO“, „TBD“, „FIXME“, „XXX“ oder „???“ (`placeholder_patterns`) | warning |
| BC-17 | Unbekannte Kennung | `depends_on` oder `parent` nennt eine Kennung, die es im Backlog nicht gibt | warning |
| BC-18 | Doppeltes Kriterium | Kriterium wiederholt ein früheres desselben Eintrags (ohne Groß-/Kleinschreibung, Leerraum und Satzzeichen am Ende) | info |

Erledigte Einträge (`done`, `closed`, `erledigt`, `abgeschlossen`) werden nicht geprüft, zählen aber als Ziel von Abhängigkeiten.

## Konfiguration

Eine JSON-Datei (`--config`); jeder Wert ist optional:

```json
{
  "language": "de",
  "rules": {"BC-04": {"enabled": false}, "BC-06": {"severity": "error"}},
  "max_estimate": 13,
  "max_criteria": 8,
  "estimate_required_top": 20,
  "duplicate_threshold": 0.8,
  "done_statuses": ["done", "closed", "erledigt", "abgeschlossen"],
  "vague_words": {"de": ["schnell", "einfach", "benutzerfreundlich", "möglichst", "etc.", "fast"]},
  "reference_date": "2026-11-12",
  "stale_days": 180,
  "epic_goal_min_words": 5,
  "ignore": [
    ["BC-02", "S-1"],
    {"rule": "BC-02", "item": "S-2", "field": "acceptance_criteria[1]"}
  ]
}
```

Ein Eintrag in `ignore` als Liste unterdrückt alle Befunde der Regel am Eintrag; als Objekt mit `field` oder `related` genau einen.

`language` ist `de`, `en` oder `auto` (beide). Zusätzlich einstellbar: `placeholder_patterns` (BC-16), `custom_rules` (siehe unten), `measurable_hints` (Ersatz je vagem Wort für die Vorschläge zu BC-02), `benefit_patterns`, `conjunctions`, `activity_patterns`, `units`, `term_stopwords`, `similarity_stopwords`, `repro_patterns` (je Sprache), `unit_conversions` und `list_separator`. BC-10 und BC-11 lassen sich höchstens auf `warning` setzen.

### Eigene Regeln

Unter `custom_rules` lassen sich eigene Regeln ohne Programmierung ergänzen: ein regulärer Ausdruck, der in den gewählten Feldern nicht vorkommen darf (`forbid`, Standard) oder vorkommen muss (`require`).

```json
{
  "custom_rules": [
    {
      "id": "TEAM-01",
      "pattern": "\\bASAP\\b",
      "title": {"de": "Dringlichkeit ohne Termin", "en": "Urgency without a date"},
      "message": {"de": "„{text}“ nennt keinen Termin.", "en": "\"{text}\" names no date."},
      "suggestion": {"de": "Nenne ein Datum statt „{text}“."}
    },
    {
      "id": "TEAM-02",
      "pattern": "(?i)dsgvo",
      "mode": "require",
      "fields": ["acceptance_criteria"],
      "kinds": ["story"],
      "severity": "info",
      "title": {"de": "Datenschutz fehlt"},
      "message": {"de": "Kein Kriterium nennt die DSGVO."}
    }
  ]
}
```

- `id`: eigene Kennung wie `TEAM-01`; `BC-` ist für die mitgelieferten Regeln reserviert.
- `fields`: `title`, `description`, `acceptance_criteria` (Standard: alle drei); `kinds`: `epic`, `story`, `bug` (Standard: alle); `severity` (Standard `warning`); `enabled` (Standard `true`).
- `forbid` meldet je Feld die erste Fundstelle; `{text}` im Text ist die Fundstelle. `require` meldet einen Befund je Eintrag, wenn keines der Felder passt.
- Die Texte (`title`, `message`, optional `suggestion`) stehen in der Konfiguration, auf Deutsch, Englisch oder beidem; fehlt eine Sprache, gilt die andere. Befunde tragen `message_key` `custom.<id>`; in Python rendert `render(key, params, "de", config.texts("de"))` sie.
- Eigene Regeln stehen in der Zusammenfassung und in SARIF hinter den mitgelieferten und lassen sich über `ignore` unterdrücken.

---

## English

Checks a backlog against fixed rules before stories go into delivery: missing or unmeasurable acceptance criteria, oversized stories, hidden dependencies, cycles, possible duplicates and contradictions. Every finding names its rule and the place in the text. No AI, standard library only. The concept ([docs/KONZEPT.md](docs/KONZEPT.md)) is written in German.

### Installation

Python 3.11 or newer. Install a fixed version from the repository:

```
pip install "git+https://github.com/seb-nsu/Backlog-Check@v0.2.0"
```

### Example

```
backlog-check backlog.csv --lang en                 # readable report in English
backlog-check backlog.json --format json            # findings and summary as JSON
backlog-check export.csv --map "Summary=title" --map "Issue key=id"
backlog-check jira-export.csv --preset jira         # ready-made mapping (also azure-devops)
backlog-check backlog.csv --format markdown         # report for wiki pages
backlog-check backlog.csv --format sarif            # SARIF 2.1.0 for code platforms
backlog-check backlog.csv --reference-date 2026-11-12  # reference date for BC-13
backlog-check backlog.csv --lang en --suggest       # add an improvement suggestion to each finding
backlog-check --template story --lang en            # new story with placeholders as JSON (also bug, epic)
backlog-check backlog.csv --fail-on warning         # warnings also give exit code 1
backlog-check backlog.csv --fix --output fixed.json # backlog with the mechanical fixes applied
```

`--suggest` adds a concrete suggestion to every finding in every format, built from the item itself (e.g. BC-04 turns "Export and print report" into "Export report" and "print report"). Without it the output is unchanged. In Python: `suggest(items, findings, config)` returns one `Suggestion` (`message_key`, `params`) per finding; `template(kind, language)` returns a new item.

Exit code: `0` without a finding of severity `error`, `1` with one, `2` for invalid input or configuration (with line number). `--fail-on warning` (or `info`) also fails on warnings (or infos); `--fail-on none` always returns `0` for valid input.

```python
from backlog_check import check, load_file, render

items = load_file("backlog.json")
for finding in check(items, {"language": "en"}):
    print(finding.item, finding.rule, render(finding.message_key, finding.params, "en"))
```

Input fields: `id`, `kind` (`epic`, `story`, `bug`) and `title` are required; `description`, `acceptance_criteria`, `estimate`, `priority` (`must`, `should`, `could`, `wont`), `rank`, `status`, `depends_on`, `parent` and `updated` (date) are optional. Findings carry `rule`, `severity`, `item`, `related`, `field`, `span`, `message_key` and `params` but never a finished sentence.

### Rules

| ID | Rule | Check | Default |
| --- | --- | --- | --- |
| BC-01 | Acceptance criteria missing | Story or bug without a criterion | error |
| BC-02 | Criterion not testable | Criterion contains a vague word ("fast", "easy", "user-friendly", …) and neither a number nor a unit | warning |
| BC-03 | Item too large | Estimate above the threshold (13) or more than 8 criteria | warning |
| BC-04 | Several concerns | Title or benefit clause joins several activities with "and" | info |
| BC-05 | Benefit missing | Story without a benefit clause ("so that", "in order to") | info |
| BC-06 | Estimate missing | Item ranked within the top 20 without an estimate | warning |
| BC-07 | Hidden dependency | Text mentions the id of another item that is not in `depends_on` | warning |
| BC-08 | Dependency in wrong order | Item ranks before, or has a higher priority than, an item it depends on | warning |
| BC-09 | Cycle | Dependencies form a cycle | error |
| BC-10 | Possible duplicate | Similarity of title and description above 0.8 | info |
| BC-11 | Conflicting values | Two items give different numbers with a unit for the same term | info |
| BC-12 | Incomplete structure | Epic without stories, or story without an epic if the backlog has epics | info |
| BC-13 | Item stale | `updated` is more than 180 days before the reference date `reference_date` (only with a reference date) | info |
| BC-14 | Steps to reproduce missing | Bug without steps to reproduce in its description | warning |
| BC-15 | Goal missing | Epic with fewer than 5 words of description | info |
| BC-16 | Placeholder not filled in | Text still contains "<…>", "TODO", "TBD", "FIXME", "XXX" or "???" (`placeholder_patterns`) | warning |
| BC-17 | Unknown id | `depends_on` or `parent` names an id that does not exist in the backlog | warning |
| BC-18 | Duplicate criterion | Criterion repeats an earlier one of the same item (ignoring case, white space and closing punctuation) | info |

Done items are not checked but still count as targets of dependencies. Configuration is described above; the keys are the same in both languages. An `ignore` entry given as an object with `field` or `related` suppresses exactly one finding.

### Custom rules

`custom_rules` in the configuration adds rules without code: a regular expression that must not (`forbid`, default) or must (`require`) occur in the chosen `fields` of the chosen `kinds`. Texts (`title`, `message`, optional `suggestion`) are given in the configuration in German, English or both; `{text}` is the match in mode `forbid`. Ids like `TEAM-01`; the prefix `BC-` is reserved. See the German section above for an example.

### Apply suggestions

`backlog-check backlog.csv --fix --output fixed.json` writes the backlog with the mechanical fixes applied as JSON in the input format and lists the changes on stderr; see the German section above.

### GitHub Action and pre-commit

See the German section above: `uses: seb-nsu/Backlog-Check@v0.2.0` in a workflow, or the hook `backlog-check` in `.pre-commit-config.yaml`.

## Lizenz / License

[MIT](LICENSE)
