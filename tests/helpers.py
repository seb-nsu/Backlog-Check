"""Helpers for golden cases: tests/golden/<rule>.json holds hand-written expectations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backlog_check import check
from backlog_check.model import RULE_IDS

GOLDEN_DIR = Path(__file__).parent / "golden"


def golden_cases(rule: str) -> list[dict[str, Any]]:
    data = json.loads((GOLDEN_DIR / f"{rule}.json").read_text(encoding="utf-8"))
    assert data["rule"] == rule
    return data["cases"]


def case_id(case: dict[str, Any]) -> str:
    return case["name"]


def run_golden(rule: str, case: dict[str, Any]) -> list[dict[str, Any]]:
    """Run only ``rule`` on the case's items and return the findings as dicts."""
    config = {"language": case["language"], **case.get("config", {})}
    config["rules"] = {r: {"enabled": r == rule} for r in RULE_IDS}
    return [finding.to_dict() for finding in check(case["items"], config)]
