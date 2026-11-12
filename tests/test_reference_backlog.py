"""Regression test on the reference backlog and the performance target from docs/KONZEPT.md."""

import io
import json
import time
from pathlib import Path

from backlog_check import check, load_file
from backlog_check.cli import main

DATA = Path(__file__).parent / "data"


def _cli_json(path: Path) -> str:
    out = io.StringIO()
    main([str(path), "--format", "json"], stdout=out)
    return out.getvalue()


def test_reference_backlog_matches_expected_output():
    expected = (DATA / "referenz-erwartung.json").read_text(encoding="utf-8")
    assert _cli_json(DATA / "referenz-backlog.json") == expected


def test_reference_backlog_csv_gives_same_output_as_json():
    assert _cli_json(DATA / "referenz-backlog.csv") == _cli_json(DATA / "referenz-backlog.json")


def test_reference_backlog_triggers_every_rule():
    findings = json.loads((DATA / "referenz-erwartung.json").read_text(encoding="utf-8"))
    assert len(findings["summary"]["by_rule"]) == 12


def _thousand_items():
    base = load_file(DATA / "referenz-backlog.json")
    items = []
    for copy in range(25):
        for item in base:
            data = {
                "id": f"{item.id}-{copy}",
                "kind": item.kind,
                "title": item.title,
                "description": item.description,
                "acceptance_criteria": list(item.acceptance_criteria),
                "estimate": item.estimate,
                "priority": item.priority,
                "rank": item.rank + 40 * copy if item.rank else None,
                "status": item.status,
                "depends_on": [f"{d}-{copy}" for d in item.depends_on],
                "parent": f"{item.parent}-{copy}" if item.parent else None,
            }
            items.append(data)
    return items[:1000]


def test_thousand_items_in_under_two_seconds():
    items = _thousand_items()
    assert len(items) == 1000
    start = time.perf_counter()
    findings = check(items)
    elapsed = time.perf_counter() - start
    assert findings
    assert elapsed < 2.0, f"{elapsed:.2f} s"
