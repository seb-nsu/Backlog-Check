import csv
import io
import json
import runpy
import sys

import pytest

from backlog_check.cli import main

CLEAN = [
    {
        "id": "S-1",
        "kind": "story",
        "title": "Rechnung herunterladen",
        "description": "Als Kundin möchte ich die Rechnung laden, damit ich sie ablegen kann.",
        "acceptance_criteria": ["Die Rechnung ist als PDF abrufbar."],
        "estimate": 3,
    }
]
WITH_ERROR = [*CLEAN, {"id": "S-2", "kind": "bug", "title": "Absturz", "rank": 1}]


def _write(tmp_path, name, content):
    path = tmp_path / name
    path.write_text(content if isinstance(content, str) else json.dumps(content), "utf-8")
    return str(path)


def _run(*args):
    out = io.StringIO()
    code = main(list(args), stdout=out)
    return code, out.getvalue()


def test_exit_code_0_without_errors(tmp_path):
    code, out = _run(_write(tmp_path, "b.json", CLEAN))
    assert code == 0
    assert "Keine Befunde." in out
    assert "Bereit: 1 von 1 Stories (100,0 %)" in out


def test_exit_code_1_with_errors_and_text_report(tmp_path):
    code, out = _run(_write(tmp_path, "b.json", WITH_ERROR))
    assert code == 1
    assert "S-2  Fehler  BC-01 Akzeptanzkriterien fehlen" in out
    assert "BC-06 Schätzung fehlt: Warnung: 1" in out
    code, out = _run(_write(tmp_path, "b.json", WITH_ERROR), "--lang", "en")
    assert "S-2  Error  BC-01 Acceptance criteria missing" in out


def test_exit_code_2_with_line_for_invalid_input(tmp_path, capsys):
    path = _write(tmp_path, "b.csv", "id,kind,title\nA,story,T\nB,task,U\n")
    code, out = _run(path)
    assert (code, out) == (2, "")
    assert "Fehler in Zeile 3: Unbekannte Art „task“" in capsys.readouterr().err


def test_exit_code_2_for_missing_file(tmp_path, capsys):
    code, _ = _run(str(tmp_path / "missing.json"), "--lang", "en")
    assert code == 2
    assert capsys.readouterr().err.startswith("Error: The file")


def test_csv_input_with_mapping_and_json_output(tmp_path):
    text = "Issue key;Summary;Issue Type;Criteria\nP-1;Login, damit ich arbeiten kann;Story;\n"
    path = _write(tmp_path, "jira.csv", text)
    code, out = _run(
        path, "--format", "json", "--map", "Issue key=id", "--map", "Summary = title",
        "--map", "Issue Type=kind", "--map", "Criteria=acceptance_criteria",
    )  # fmt: skip
    data = json.loads(out)
    assert code == 1
    assert [f["rule"] for f in data["findings"]] == ["BC-01"]
    assert data["summary"]["ready_stories"] == 0


def test_csv_output_and_output_file(tmp_path):
    items = [{**CLEAN[0], "acceptance_criteria": ["Die Suche ist schnell."], "id": "S-9"}]
    target = tmp_path / "out.csv"
    code, out = _run(_write(tmp_path, "b.json", items), "--format", "csv", "--output", str(target))
    assert (code, out) == (0, "")
    rows = list(csv.DictReader(io.StringIO(target.read_text("utf-8"))))
    assert rows[0]["rule"] == "BC-02"
    assert (rows[0]["span_start"], rows[0]["span_end"]) == ("14", "21")
    assert json.loads(rows[0]["params"]) == {"word": "schnell"}
    assert rows[0]["message"].startswith("Das Kriterium enthält „schnell“")


def test_text_report_shows_excerpt_and_related(tmp_path):
    items = [
        {**CLEAN[0], "acceptance_criteria": ["Die Suche ist schnell."]},
        {**CLEAN[0], "id": "S-2", "description": CLEAN[0]["description"] + " Siehe S-1."},
    ]
    _, out = _run(_write(tmp_path, "b.json", items))
    assert "(Feld acceptance_criteria[0]; Textstelle „schnell“)" in out
    assert "(Feld description; Textstelle „S-1“; betrifft auch S-1)" in out
    assert "betrifft auch S-1)" in out


def test_config_file_and_language(tmp_path):
    items = [{**CLEAN[0], "acceptance_criteria": ["Loading is fast."]}]
    path = _write(tmp_path, "b.json", items)
    config = _write(tmp_path, "c.json", {"rules": {"BC-02": {"severity": "error"}}})
    code, out = _run(path, "--lang", "en", "--config", config)
    assert code == 1
    assert "BC-02 Criterion not testable: Error: 1" in out
    config = _write(tmp_path, "c.json", {"language": "de"})
    assert _run(path, "--lang", "en", "--config", config)[0] == 0


@pytest.mark.parametrize(
    ("config", "message"),
    [
        ("{", "Fehler in Zeile 1: Die Konfiguration ist kein gültiges JSON"),
        ("[]", "Fehler: Die Konfiguration muss ein JSON-Objekt sein."),
        ('{"max_estimate": "x"}', "Fehler: Ungültiger Wert 'x'"),
    ],
)
def test_invalid_config(tmp_path, capsys, config, message):
    path = _write(tmp_path, "b.json", CLEAN)
    assert _run(path, "--config", _write(tmp_path, "c.json", config))[0] == 2
    assert capsys.readouterr().err.startswith(message)


def test_missing_config_file(tmp_path, capsys):
    path = _write(tmp_path, "b.json", CLEAN)
    assert _run(path, "--config", str(tmp_path / "none.json"))[0] == 2
    assert "Konfigurationsdatei" in capsys.readouterr().err


@pytest.mark.parametrize("entry", ["Summary", "=title", "Summary=name"])
def test_invalid_mapping(tmp_path, capsys, entry):
    assert _run(_write(tmp_path, "b.json", CLEAN), "--map", entry)[0] == 2
    assert "Ungültige Zuordnung" in capsys.readouterr().err


def test_separator_from_option_and_config(tmp_path):
    path = _write(tmp_path, "b.csv", "id,kind,title,depends_on\nA,bug,T,B;C\nB,bug,U,\nC,bug,V,\n")
    _, out = _run(path, "--format", "json", "--separator", ";")
    assert "BC-01" in out and "BC-09" not in out
    config = _write(tmp_path, "c.json", {"list_separator": ";"})
    _, out_config = _run(path, "--format", "json", "--config", config, "--delimiter", ",")
    assert out_config == out


def test_output_is_byte_identical(tmp_path):
    path = _write(tmp_path, "b.json", WITH_ERROR)
    for fmt in ("text", "json", "csv"):
        assert _run(path, "--format", fmt) == _run(path, "--format", fmt)


def test_default_stdout_and_module_entry(tmp_path, capsys, monkeypatch):
    path = _write(tmp_path, "b.json", CLEAN)
    assert main([path, "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["findings"] == []
    monkeypatch.setattr(sys, "argv", ["backlog-check", path])
    with pytest.raises(SystemExit) as info:
        runpy.run_module("backlog_check", run_name="__main__")
    assert info.value.code == 0


def test_text_report_without_field_and_without_stories(tmp_path):
    path = _write(tmp_path, "b.json", [{"id": "E-1", "kind": "epic", "title": "Abrechnung"}])
    code, out = _run(path)
    assert code == 0
    assert "    Das Epic hat keine Stories.\n\n" in out
    assert "Bereit: keine offenen Stories" in out


def test_markdown_output(tmp_path):
    items = [{**CLEAN[0], "title": "A|B", "acceptance_criteria": []}]
    code, out = _run(_write(tmp_path, "b.json", items), "--format", "markdown")
    assert code == 1
    assert out.startswith("# backlog-check\n")
    assert "| Eintrag | Schwere | Regel | Befund | Feld |" in out
    assert "| S-1 | Fehler | BC-01 Akzeptanzkriterien fehlen | Es fehlen Akzeptanzkriterien." in out
    assert "## Zusammenfassung" in out
    config = _write(tmp_path, "c.json", {"language": "de"})
    path = _write(tmp_path, "b.json", CLEAN)
    _, out = _run(path, "--format", "markdown", "--lang", "en", "--config", config)
    assert "No findings." in out and "| Item |" not in out


def test_markdown_escapes_pipes():
    from backlog_check import Config, Finding, Item
    from backlog_check.cli import Report, format_markdown

    finding = Finding("BC-02", "warning", "A", "bc02.unmeasurable", {"word": "a|b"})
    summary = {
        "items": 1,
        "checked": 1,
        "findings": 1,
        "by_severity": {"info": 0, "warning": 1, "error": 0},
        "by_rule": {},
        "stories": 0,
        "ready_stories": 0,
        "ready_ratio": None,
    }
    report = Report([Item("A", "story", "T")], [finding], summary, "de", Config(), "b.json")
    assert "„a\\|b“" in format_markdown(report)


def test_sarif_output(tmp_path):
    path = _write(tmp_path, "b.json", WITH_ERROR)
    code, out = _run(path, "--format", "sarif", "--lang", "en")
    sarif = json.loads(out)
    assert code == 1
    assert sarif["version"] == "2.1.0"
    run = sarif["runs"][0]
    assert [r["id"] for r in run["tool"]["driver"]["rules"]][:2] == ["BC-01", "BC-02"]
    first = next(r for r in run["results"] if r["ruleId"] == "BC-01")
    assert first["level"] == "error"
    assert first["message"]["text"] == "Acceptance criteria are missing."
    location = first["locations"][0]
    assert location["physicalLocation"]["region"] == {"startLine": 1}
    assert location["logicalLocations"] == [{"name": "S-2", "kind": "object"}]
    assert first["properties"]["message_key"] == "bc01.missing"
    assert {r["level"] for r in run["results"]} == {"error", "warning", "note"}


def test_sarif_without_source_lines():
    from backlog_check import Config, Item, check, summarize
    from backlog_check.cli import Report, format_sarif

    items = [Item("A", "story", "T")]
    findings = check(items)
    report = Report(items, findings, summarize(items, findings), "de", Config(), "b.json")
    result = json.loads(format_sarif(report))["runs"][0]["results"][0]
    assert "region" not in result["locations"][0]["physicalLocation"]
    assert {r["level"] for r in json.loads(format_sarif(report))["runs"][0]["results"]} >= {"note"}


def test_reference_date_option(tmp_path):
    items = [{**CLEAN[0], "updated": "2026-01-01"}]
    path = _write(tmp_path, "b.json", items)
    _, out = _run(path, "--format", "json")
    assert json.loads(out)["findings"] == []
    _, out = _run(path, "--format", "json", "--reference-date", "2026-11-12")
    assert [f["rule"] for f in json.loads(out)["findings"]] == ["BC-13"]
    config = _write(tmp_path, "c.json", {"reference_date": "2026-02-01"})
    _, out = _run(path, "--format", "json", "--reference-date", "2026-11-12", "--config", config)
    assert json.loads(out)["findings"] == []
