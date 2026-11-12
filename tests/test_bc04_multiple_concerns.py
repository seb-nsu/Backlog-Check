import pytest

from helpers import case_id, golden_cases, run_golden

RULE = "BC-04"


@pytest.mark.parametrize("case", golden_cases(RULE), ids=case_id)
def test_bc04_golden(case):
    assert run_golden(RULE, case) == case["expected"]


def test_bc04_one_finding_per_field():
    case = {
        "language": "de",
        "items": [
            {
                "id": "A",
                "kind": "story",
                "title": "lesen und schreiben und rechnen",
                "description": "Ohne Nutzen. Damit es klappt. Damit A und B lesen und rechnen.",
            }
        ],
    }
    found = run_golden(RULE, case)
    assert [(f["field"], f["span"]) for f in found] == [
        ("title", [6, 9]),
        ("description", [50, 53]),
    ]
