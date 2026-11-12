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
                "title": "Lesen und Schreiben und Rechnen",
                "description": "Ohne Nutzen. Damit es klappt. Damit A und B und C.",
            }
        ],
    }
    found = run_golden(RULE, case)
    assert [(f["field"], f["span"]) for f in found] == [
        ("title", [6, 9]),
        ("description", [38, 41]),
    ]
