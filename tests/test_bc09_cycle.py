import pytest

from backlog_check.rules.bc09_cycle import strongly_connected
from helpers import case_id, golden_cases, run_golden

RULE = "BC-09"


@pytest.mark.parametrize("case", golden_cases(RULE), ids=case_id)
def test_bc09_golden(case):
    assert run_golden(RULE, case) == case["expected"]


def test_bc09_strongly_connected_components():
    graph = {"a": ["b"], "b": ["c", "a"], "c": ["d"], "d": ["c"], "e": ["a"]}
    assert strongly_connected(graph) == [["d", "c"], ["b", "a"], ["e"]]
