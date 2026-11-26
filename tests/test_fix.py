"""Applying the mechanical fixes (--fix, apply_fixes)."""

import io
import json

from backlog_check import Change, apply_fixes, check
from backlog_check.cli import main

ITEMS = [
    {"id": "E-1", "kind": "epic", "title": "Rechnungen", "description": "Rechnungen für Kunden"},
    {
        "id": "S-1",
        "kind": "story",
        "title": "Rechnung erstellen und versenden",
        "description": "Als Kundin möchte ich die Rechnung, damit ich zahle. Siehe S-2.",
        "acceptance_criteria": ["Die Rechnung ist ein PDF.", "die Rechnung ist ein PDF"],
        "estimate": 3,
        "priority": "must",
        "parent": "E-1",
    },
    {"id": "S-1-2", "kind": "story", "title": "Rechnungen archivieren", "parent": "E-1"},
    {"id": "S-2", "kind": "story", "title": "Mahnung zu Rechnungen", "status": "offen"},
    {"id": "S-3", "kind": "story", "title": "Mahnung drucken", "parent": "X-9"},
]
CONFIG = {"rules": {"BC-01": {"enabled": False}, "BC-05": {"enabled": False}}}


def _fix(items=ITEMS, config=CONFIG):
    return apply_fixes(items, check(items, config), config)


def test_applies_split_dependency_epic_and_duplicate_criterion():
    fixed, changes = _fix()
    assert [c.to_dict() for c in changes] == [
        {
            "rule": "BC-04",
            "item": "S-1",
            "message_key": "fix.split_item",
            "params": {
                "first": "Rechnung erstellen",
                "new_id": "S-1-3",
                "second": "Rechnung versenden",
            },
        },
        {
            "rule": "BC-07",
            "item": "S-1",
            "message_key": "fix.add_dependency",
            "params": {"id": "S-2"},
        },
        {
            "rule": "BC-18",
            "item": "S-1",
            "message_key": "fix.remove_criterion",
            "params": {"field": "acceptance_criteria[1]", "first": "acceptance_criteria[0]"},
        },
        {
            "rule": "BC-12",
            "item": "S-2",
            "message_key": "fix.set_parent",
            "params": {"epic": "E-1"},
        },
    ]
    assert [item["id"] for item in fixed] == ["E-1", "S-1", "S-1-3", "S-1-2", "S-2", "S-3"]
    assert fixed[1] == {
        "id": "S-1",
        "kind": "story",
        "title": "Rechnung erstellen",
        "description": "Als Kundin möchte ich die Rechnung, damit ich zahle. Siehe S-2.",
        "acceptance_criteria": ["Die Rechnung ist ein PDF."],
        "estimate": 3,
        "priority": "must",
        "depends_on": ["S-2"],
        "parent": "E-1",
    }
    assert fixed[2] == {
        "id": "S-1-3",
        "kind": "story",
        "title": "Rechnung versenden",
        "priority": "must",
        "parent": "E-1",
    }
    assert fixed[4]["parent"] == "E-1"
    assert fixed[5]["parent"] == "X-9"  # unknown parent is left for the author


def test_fixed_backlog_resolves_the_fixed_findings():
    fixed, _ = _fix()
    rules = {(f.rule, f.item) for f in check(fixed, CONFIG)}
    assert not rules & {("BC-07", "S-1"), ("BC-18", "S-1"), ("BC-12", "S-2"), ("BC-04", "S-1")}


def test_nothing_to_fix_and_unsplittable_title():
    items = [
        {"id": "S-1", "kind": "story", "title": "und drucken"},
        {"id": "S-2", "kind": "story", "title": "Eintrag ohne Epic"},
        {"id": "E-1", "kind": "epic", "title": "Zahlung"},
    ]
    fixed, changes = _fix(items)
    assert changes == []
    assert fixed == [
        {"id": "S-1", "kind": "story", "title": "und drucken"},
        {"id": "S-2", "kind": "story", "title": "Eintrag ohne Epic"},
        {"id": "E-1", "kind": "epic", "title": "Zahlung"},
    ]


def test_bc04_in_description_is_not_fixed():
    items = [
        {
            "id": "S-1",
            "kind": "story",
            "title": "Rechnung",
            "description": "Als Kundin möchte ich, damit ich prüfen und zahlen kann.",
        }
    ]
    findings = check(items, CONFIG)
    assert [f.field for f in findings if f.rule == "BC-04"] == ["description"]
    assert apply_fixes(items, findings, CONFIG)[1] == []


def test_change_to_dict_sorts_params():
    change = Change("BC-07", "S-1", "fix.add_dependency", {"z": 1, "a": 2})
    assert list(change.to_dict()["params"]) == ["a", "z"]


def test_command_line_fix(tmp_path, capsys):
    path = tmp_path / "b.json"
    path.write_text(json.dumps(ITEMS), "utf-8")
    config = tmp_path / "c.json"
    config.write_text(json.dumps(CONFIG), "utf-8")
    out = io.StringIO()
    code = main([str(path), "--fix", "--config", str(config)], out)
    assert code == 0
    assert json.loads(out.getvalue()) == _fix()[0]
    err = capsys.readouterr().err
    assert "S-1  BC-07  Abhängigkeit S-2 ergänzt." in err
    assert err.endswith("4 Änderungen\n")
    target = tmp_path / "fixed.json"
    main([str(path), "--fix", "--lang", "en", "--output", str(target)], io.StringIO())
    assert json.loads(target.read_text("utf-8"))[0]["id"] == "E-1"
    assert "changes" in capsys.readouterr().err
