import pytest

from helpers import case_id, golden_cases, run_golden

RULE = "BC-12"


@pytest.mark.parametrize("case", golden_cases(RULE), ids=case_id)
def test_bc12_golden(case):
    assert run_golden(RULE, case) == case["expected"]


def test_bc12_epic_with_only_bugs_has_no_stories():
    case = {
        "language": "de",
        "items": [
            {"id": "E", "kind": "epic", "title": "Epic"},
            {"id": "B", "kind": "bug", "title": "Bug", "parent": "E"},
        ],
    }
    assert [f["message_key"] for f in run_golden(RULE, case)] == ["bc12.epic_without_stories"]
