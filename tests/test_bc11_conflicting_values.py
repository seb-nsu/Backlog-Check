import pytest

from helpers import case_id, golden_cases, run_golden

RULE = "BC-11"


@pytest.mark.parametrize("case", golden_cases(RULE), ids=case_id)
def test_bc11_golden(case):
    assert run_golden(RULE, case) == case["expected"]


def test_bc11_skips_unknown_units_terms_and_repeated_pairs():
    case = {
        "language": "de",
        "items": [
            {"id": "A", "kind": "story", "title": "Frist 5 Tage", "description": "Version 2 Beta."},
            {
                "id": "B",
                "kind": "story",
                "title": "Frist 7 Tage",
                "description": "4 Tage. Frist 8 Tage. Version 3 Beta.",
            },
            {"id": "C", "kind": "story", "title": "Quote 2,5 % und Quote 2,50 %"},
            {"id": "D", "kind": "story", "title": "Quote 3 %"},
        ],
    }
    found = run_golden(RULE, case)
    assert [(f["item"], f["related"], f["params"]["value"]) for f in found] == [
        ("B", ["A"], "7"),
        ("D", ["C"], "3"),
    ]
