import pytest

from helpers import case_id, golden_cases, run_golden

RULE = "BC-07"


@pytest.mark.parametrize("case", golden_cases(RULE), ids=case_id)
def test_bc07_golden(case):
    assert run_golden(RULE, case) == case["expected"]
