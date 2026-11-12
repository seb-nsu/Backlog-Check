"""Acceptance criteria from docs/KONZEPT.md that concern the package as a whole."""

import json

from backlog_check import check
from backlog_check.model import RULE_IDS

ITEMS = [
    {"id": "A-1", "kind": "story", "title": "Export und Druck", "estimate": 20, "rank": 1},
    {
        "id": "A-2",
        "kind": "story",
        "title": "Suche",
        "acceptance_criteria": ["Die Suche ist schnell."],
        "depends_on": ["A-3"],
        "rank": 2,
    },
    {"id": "A-3", "kind": "bug", "title": "Absturz", "depends_on": ["A-2"], "rank": 3},
]


def _rules(findings):
    return [(f.item, f.rule) for f in findings]


def test_findings_are_sorted_by_position_then_rule():
    found = _rules(check(ITEMS))
    assert found == sorted(found, key=lambda pair: (["A-1", "A-2", "A-3"].index(pair[0]), pair[1]))
    assert ("A-1", "BC-01") in found and ("A-2", "BC-02") in found and ("A-2", "BC-09") in found


def test_disabled_rule_creates_no_finding():
    for rule in RULE_IDS:
        found = check(ITEMS, {"rules": {rule: {"enabled": False}}})
        assert rule not in {f.rule for f in found}


def test_changed_threshold_takes_effect():
    assert ("A-1", "BC-03") in _rules(check(ITEMS))
    assert ("A-1", "BC-03") not in _rules(check(ITEMS, {"max_estimate": 20}))


def test_changed_severity_takes_effect():
    found = check(ITEMS, {"rules": {"BC-01": {"severity": "warning"}}})
    assert {f.severity for f in found if f.rule == "BC-01"} == {"warning"}


def test_ignore_suppresses_exactly_that_finding():
    before = check(ITEMS)
    after = check(ITEMS, {"ignore": [["BC-01", "A-1"]]})
    removed = [f for f in before if f not in after]
    assert _rules(removed) == [("A-1", "BC-01")]
    assert len(after) == len(before) - 1


def test_findings_contain_no_sentences():
    for finding in check(ITEMS):
        data = finding.to_dict()
        assert set(data) == {
            "rule", "severity", "item", "related", "field", "span", "message_key", "params",
        }  # fmt: skip
        assert " " not in data["message_key"]


def test_same_input_gives_byte_identical_output():
    def run():
        return json.dumps([f.to_dict() for f in check(ITEMS, {"language": "auto"})]).encode()

    assert run() == run()


def test_ignore_with_field_suppresses_one_of_several_findings():
    items = [
        {
            "id": "B-1",
            "kind": "story",
            "title": "Suche, damit ich finde",
            "acceptance_criteria": ["Die Suche ist schnell.", "Die Maske ist einfach."],
        },
        {"id": "B-2", "kind": "story", "title": "Hängt an B-1 und B-3"},
        {"id": "B-3", "kind": "story", "title": "Drei"},
    ]
    only = {"rules": {r: {"enabled": r in ("BC-02", "BC-07")} for r in RULE_IDS}}
    before = check(items, only)
    entry = {"rule": "BC-02", "item": "B-1", "field": "acceptance_criteria[1]"}
    after = check(items, {**only, "ignore": [entry]})
    assert [f for f in before if f not in after] == [before[1]]
    entry = {"rule": "BC-07", "item": "B-2", "related": "B-3"}
    after = check(items, {**only, "ignore": [entry]})
    assert [f.related for f in before if f not in after] == [("B-3",)]
