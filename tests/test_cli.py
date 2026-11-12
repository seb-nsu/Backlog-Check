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
