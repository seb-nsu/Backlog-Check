import pytest

from helpers import case_id, golden_cases, run_golden

RULE = "BC-08"


@pytest.mark.parametrize("case", golden_cases(RULE), ids=case_id)
def test_bc08_golden(case):
    assert run_golden(RULE, case) == case["expected"]


def test_bc08_one_finding_per_pair_and_no_self_reference():
    case = {
        "language": "de",
        "items": [
            {"id": "A", "kind": "story", "title": "T", "rank": 1, "depends_on": ["A", "B", "B"]},
            {"id": "B", "kind": "story", "title": "U", "rank": 2},
        ],
    }
    assert [f["field"] for f in run_golden(RULE, case)] == ["depends_on[1]"]
