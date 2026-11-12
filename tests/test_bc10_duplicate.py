import pytest

from helpers import case_id, golden_cases, run_golden

RULE = "BC-10"


@pytest.mark.parametrize("case", golden_cases(RULE), ids=case_id)
def test_bc10_golden(case):
    assert run_golden(RULE, case) == case["expected"]


def _items(*titles):
    return [{"id": f"I-{n}", "kind": "story", "title": t} for n, t in enumerate(titles)]


def test_bc10_threshold_is_configurable():
    case = {
        "language": "en",
        "config": {"duplicate_threshold": 0.4},
        "items": _items("a b c", "a b d"),
    }
    assert [f["params"] for f in run_golden(RULE, case)] == [{"other": "I-0", "similarity": 0.5}]
    case["config"] = {"duplicate_threshold": 0.5}
    assert run_golden(RULE, case) == []
    case["config"] = {"duplicate_threshold": 0}
    case["items"] = _items("x z", "y z")
    assert len(run_golden(RULE, case)) == 1


def test_bc10_finds_all_earlier_duplicates_and_skips_empty_text():
    case = {
        "language": "en",
        "items": _items("same words here", "!!!", "Same words here", "same, words, here"),
    }
    found = run_golden(RULE, case)
    assert [(f["item"], f["related"]) for f in found] == [
        ("I-2", ["I-0"]),
        ("I-3", ["I-0"]),
        ("I-3", ["I-2"]),
    ]


def test_bc10_threshold_above_one_never_triggers():
    case = {"language": "en", "config": {"duplicate_threshold": 1.5}, "items": _items("a", "a")}
    assert run_golden(RULE, case) == []
