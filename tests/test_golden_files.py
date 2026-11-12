"""Every rule has golden cases that trigger and that narrowly do not, in German and English."""

import pytest

from backlog_check.model import RULE_IDS
from helpers import golden_cases


@pytest.mark.parametrize("rule", RULE_IDS)
def test_golden_cases_cover_both_languages(rule):
    cases = golden_cases(rule)
    names = {case["name"] for case in cases}
    assert {"de-trigger", "de-near-miss", "en-trigger", "en-near-miss"} <= names
    for case in cases:
        assert case["language"] == case["name"][:2]
        if "trigger" in case["name"]:
            assert case["expected"]
            assert all(f["rule"] == rule for f in case["expected"])
        else:
            assert case["expected"] == []
