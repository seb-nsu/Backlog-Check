"""BC-03: estimate above the threshold or more criteria than allowed."""

from __future__ import annotations

from collections.abc import Iterator

from ..context import Context
from ..model import Finding

RULE = "BC-03"


def check_bc03(ctx: Context) -> Iterator[Finding]:
    max_estimate = ctx.config.max_estimate
    max_criteria = ctx.config.max_criteria
    # ASSUMPTION: the rule applies to every kind, epics included ("Eintrag").
    for item in ctx.active:
        if item.estimate is not None and item.estimate > max_estimate:
            yield ctx.finding(
                RULE,
                item,
                "bc03.estimate_too_large",
                params={"estimate": item.estimate, "max_estimate": max_estimate},
                field="estimate",
            )
        if len(item.acceptance_criteria) > max_criteria:
            yield ctx.finding(
                RULE,
                item,
                "bc03.too_many_criteria",
                params={"count": len(item.acceptance_criteria), "max_criteria": max_criteria},
                field="acceptance_criteria",
            )
