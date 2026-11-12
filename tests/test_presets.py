import io
import json

import pytest

from backlog_check import InputError, load_csv, load_json
from backlog_check.cli import main
from backlog_check.presets import PRESETS

JIRA = (
    "Issue key,Issue Type,Summary,Description,Custom field (Story Points),"
    "Custom field (Story point estimate),Status,Custom field (Epic Link),Updated,Priority\n"
    "P-1,Epic,Abrechnung,Kunden laden Rechnungen selbst herunter.,,,To Do,,12/Nov/26 1:06 PM,High\n"
    'P-2,Story,Rechnung laden,"Als Kundin möchte ich laden, damit ich ablege.",3,,Done,P-1,,Low\n'
    "P-3,Sub-task,Teilaufgabe,,,2,To Do,P-1,,Medium\n"
)

AZURE = (
    "ID,Work Item Type,Title,Description,Acceptance Criteria,Effort,State,Parent\n"
    "7,Feature,Abrechnung,<div>Kunden laden Rechnungen selbst herunter.</div>,,,New,\n"
    '8,Product Backlog Item,Rechnung laden,"<p>Als Kundin &amp; Leserin</p>",'
    '"<ul><li>Eins</li><li>Zwei<br>Drei</li></ul>",5,Done,7\n'
)


def test_jira_preset():
    epic, story, task = load_csv(JIRA, preset=PRESETS["jira"])
    assert (epic.kind, epic.updated) == ("epic", "2026-11-12")
    assert (story.kind, story.estimate, story.status, story.parent) == ("story", 3, "Done", "P-1")
    assert (task.kind, task.estimate) == ("story", None)


def test_azure_devops_preset_converts_html():
    feature, pbi = load_csv(AZURE, preset=PRESETS["azure-devops"])
    assert (feature.id, feature.kind) == ("7", "epic")
    assert feature.description == "Kunden laden Rechnungen selbst herunter."
    assert pbi.kind == "story"
    assert pbi.description == "Als Kundin & Leserin"
    assert pbi.acceptance_criteria == ("Eins", "Zwei", "Drei")
    assert (pbi.estimate, pbi.parent) == (5, "7")


def test_mapping_wins_over_preset():
    (story,) = load_csv(
        "Issue key,Issue Type,Summary,Name\nP-1,Story,Old,New\n",
        {"Name": "title", "Summary": "ignored"},
        preset=PRESETS["jira"],
    )
    assert story.title == "New"


def test_preset_for_json():
    jira = PRESETS["jira"]
    data = [{"Issue key": "P-1", "Issue Type": "Sub-task", "Summary": "T", "Status": "Done"}]
    (item,) = load_json(json.dumps(data), None, jira)
    assert (item.id, item.kind, item.status) == ("P-1", "story", "Done")
    data = [{"Issue key": "P-1", "kind": "bug", "Summary": "T", "Votes": 1}]
    assert load_json(json.dumps(data), None, jira)[0].kind == "bug"
    with pytest.raises(InputError) as info:
        load_json(json.dumps([{"Issue key": "P-1", "Summary": "T"}]), None, jira)
    assert info.value.params == {"field": "kind"}


def test_cli_preset(tmp_path):
    path = tmp_path / "jira.csv"
    path.write_text(JIRA, encoding="utf-8")
    out = io.StringIO()
    main([str(path), "--preset", "jira", "--format", "json"], stdout=out)
    rules = {(f["item"], f["rule"]) for f in json.loads(out.getvalue())["findings"]}
    assert ("P-3", "BC-01") in rules
