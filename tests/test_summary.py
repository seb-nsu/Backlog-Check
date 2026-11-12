from backlog_check import Finding, Item, check, summarize


def test_summary_counts_and_ready_share():
    items = [
        Item("E", "epic", "Epic"),
        Item("A", "story", "Story A"),
        Item("B", "story", "Story B", acceptance_criteria=("ok",)),
        Item("C", "story", "Story C", status="done"),
        Item("D", "bug", "Bug D"),
    ]
    findings = [
        Finding("BC-01", "error", "A", "bc01.missing"),
        Finding("BC-01", "error", "D", "bc01.missing"),
        Finding("BC-05", "info", "B", "bc05.missing_benefit"),
        Finding("BC-10", "warning", "B", "bc10.possible_duplicate"),
        Finding("BC-10", "info", "B", "bc10.possible_duplicate"),
    ]
    assert summarize(items, findings) == {
        "items": 5,
        "checked": 4,
        "findings": 5,
        "by_severity": {"info": 2, "warning": 1, "error": 2},
        "by_rule": {
            "BC-01": {"error": 2},
            "BC-05": {"info": 1},
            "BC-10": {"info": 1, "warning": 1},
        },
        "stories": 2,
        "ready_stories": 1,
        "ready_ratio": 0.5,
    }


def test_summary_without_stories():
    items = [{"id": "E", "kind": "epic", "title": "Epic"}]
    summary = summarize(items, check(items), {"done_statuses": ["x"]})
    assert summary["stories"] == 0
    assert summary["ready_ratio"] is None
    assert summary["by_rule"] == {"BC-12": {"info": 1}}
