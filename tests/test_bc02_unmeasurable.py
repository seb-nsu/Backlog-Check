import pytest

from helpers import case_id, golden_cases, run_golden

RULE = "BC-02"


@pytest.mark.parametrize("case", golden_cases(RULE), ids=case_id)
def test_bc02_golden(case):
    assert run_golden(RULE, case) == case["expected"]


def test_bc02_auto_language_checks_both_word_lists():
    case = {
        "language": "auto",
        "items": [
            {"id": "A", "kind": "story", "title": "T", "acceptance_criteria": ["Easy, einfach"]}
        ],
    }
    assert [f["params"]["word"] for f in run_golden(RULE, case)] == ["Easy", "einfach"]


def test_bc02_extended_word_list():
    case = {
        "language": "de",
        "config": {"vague_words": {"de": ["zügig"]}},
        "items": [
            {"id": "A", "kind": "story", "title": "T", "acceptance_criteria": ["Zügig, schnell"]}
        ],
    }
    assert [f["params"]["word"] for f in run_golden(RULE, case)] == ["Zügig"]
